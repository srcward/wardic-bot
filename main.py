import discord, os, logging, asyncpg, asyncio, json, random, ssl
from discord.ext import commands
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse
from utils.cache import Cache

logging.basicConfig(
    level=logging.INFO,
    format="[{asctime}] [{levelname}] {name}: {message}",
    datefmt="%H:%M:%S",
    style="{",
)

log = logging.getLogger("Bot")
cog_log = logging.getLogger("Cogs")
db_log = logging.getLogger("Database")

load_dotenv()
_token = os.getenv("DISCORD_TOKEN")
_database_url = os.getenv("DATABASE_URL")
_fallback_prefix = os.getenv("FALLBACK_PREFIX")

logging.getLogger("discord").setLevel(logging.WARNING)


class Database:
    def __init__(self):
        self.pool = None
        self.listener_conn = None

    async def connect(self):
        if not _database_url:
            db_log.error(
                "DATABASE_URL is not set. Please set the DATABASE_URL environment variable."
            )
            raise ValueError("DATABASE_URL environment variable is not set.")

        parsed = urlparse(_database_url)
        host = parsed.hostname
        if not host:
            db_log.error(
                "DATABASE_URL does not contain a valid host. Please verify the DSN."
            )
            raise ValueError("DATABASE_URL is missing a hostname or is malformed.")

        use_ssl = True
        if host in ("localhost", "127.0.0.1", "::1"):
            use_ssl = False

        ssl_ctx = None
        if use_ssl:
            try:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = True
                ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            except Exception as e:
                db_log.warning(
                    f"Failed to create SSL context for DB connection: {e}. Proceeding without explicit SSL context."
                )
                ssl_ctx = None

        try:
            db_log.info("Creating database connection pool...")
            self.pool = await asyncpg.create_pool(
                _database_url,
                min_size=5,
                max_size=10,
                ssl=ssl_ctx if ssl_ctx is not None else None,
            )
            db_log.info("Database connection pool created")
        except Exception as e:
            db_log.error(f"Failed to connect to database: {e}")
            raise

    async def close(self):
        if self.listener_conn:
            try:
                await self.listener_conn.close()
            except Exception:
                pass
        if self.pool:
            try:
                await self.pool.close()
                db_log.info("Database connection pool closed")
            except Exception:
                pass

    async def _execute_bot(self, conn, query, *args):
        await conn.execute("SET LOCAL bot.is_updating = 'true';")
        return await conn.execute(query, *args)

    async def execute(self, query: str, *args, bot_update: bool = False):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if bot_update:
                    return await self._execute_bot(conn, query, *args)
                return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def start_listener(self, callback):
        if not _database_url:
            db_log.error("DATABASE_URL is not set. Cannot start listener.")
            raise ValueError("DATABASE_URL environment variable is not set.")

        parsed = urlparse(_database_url)
        host = parsed.hostname
        if not host:
            db_log.error(
                "DATABASE_URL does not contain a valid host. Cannot start listener."
            )
            raise ValueError("DATABASE_URL is missing a hostname or is malformed.")

        use_ssl = True
        if host in ("localhost", "127.0.0.1", "::1"):
            use_ssl = False

        ssl_ctx = None
        if use_ssl:
            try:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = True
                ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            except Exception as e:
                db_log.warning(
                    f"Failed to create SSL context for listener: {e}. Trying without explicit SSL context."
                )
                ssl_ctx = None

        try:
            self.listener_conn = await asyncpg.connect(
                _database_url, ssl=ssl_ctx if ssl_ctx is not None else None
            )
            await self.listener_conn.add_listener("cache_invalidate", callback)
            db_log.info("Started listening for cache invalidation events")
        except Exception as e:
            db_log.error(f"Failed to start listener connection: {e}")
            if self.listener_conn:
                try:
                    await self.listener_conn.close()
                except Exception:
                    pass
                self.listener_conn = None
            raise


class BotCache:
    def __init__(self):
        self.guilds = Cache(
            Cache.MEMORY,
            namespace="guilds",
            ttl=int(timedelta(minutes=10).total_seconds()),
        )
        self.members = Cache(
            Cache.MEMORY,
            namespace="members",
            ttl=int(timedelta(minutes=10).total_seconds()),
        )
        self.users = Cache(
            Cache.MEMORY,
            namespace="users",
            ttl=int(timedelta(minutes=10).total_seconds()),
        )
        self.config = Cache(
            Cache.MEMORY,
            namespace="config",
            ttl=int(timedelta(minutes=5).total_seconds()),
        )
        self.snipes = Cache(
            Cache.MEMORY,
            namespace="snipes",
            ttl=int(timedelta(hours=2).total_seconds()),
        )

    async def clear_all(self):
        await self.guilds.clear()
        await self.members.clear()
        await self.users.clear()
        await self.config.clear()

    async def cleanup_all_expired(self) -> int:
        total = 0
        total += await self.guilds.cleanup_expired()
        total += await self.members.cleanup_expired()
        total += await self.users.cleanup_expired()
        total += await self.config.cleanup_expired()
        return total


class DatabaseFunctions:
    def __init__(self, db: Database, cache: BotCache):
        self.db = db
        self.cache = cache

    async def init_tables(self):
        q = """
        CREATE TABLE IF NOT EXISTS guilds (
            id BIGINT PRIMARY KEY,
            data JSONB DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS members (
            guild_id BIGINT NOT NULL,
            member_id BIGINT NOT NULL,
            data JSONB DEFAULT '{}',
            PRIMARY KEY (guild_id, member_id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            data JSONB DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS configuration (
            active BOOL PRIMARY KEY DEFAULT TRUE,
            data JSONB DEFAULT '{}'
        );
        """
        await self.db.execute(q, bot_update=True)

        await self.db.execute(
            """
            CREATE OR REPLACE FUNCTION notify_cache_invalidate()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Skip invalidation if the bot marked this transaction
                IF current_setting('bot.is_updating', true) = 'true' THEN
                    RETURN NEW;
                END IF;

                IF TG_TABLE_NAME = 'guilds' THEN
                    PERFORM pg_notify('cache_invalidate', json_build_object(
                        'table', 'guilds',
                        'id', COALESCE(NEW.id, OLD.id)
                    )::text);

                ELSIF TG_TABLE_NAME = 'members' THEN
                    PERFORM pg_notify('cache_invalidate', json_build_object(
                        'table', 'members',
                        'guild_id', COALESCE(NEW.guild_id, OLD.guild_id),
                        'member_id', COALESCE(NEW.member_id, OLD.member_id)
                    )::text);

                ELSIF TG_TABLE_NAME = 'users' THEN
                    PERFORM pg_notify('cache_invalidate', json_build_object(
                        'table', 'users',
                        'id', COALESCE(NEW.id, OLD.id)
                    )::text);

                ELSIF TG_TABLE_NAME = 'configuration' THEN
                    PERFORM pg_notify('cache_invalidate', json_build_object(
                        'table', 'configuration',
                        'id', 'config'
                    )::text);
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
            bot_update=True,
        )

        for table in ["guilds", "members", "users", "configuration"]:
            await self.db.execute(
                f"DROP TRIGGER IF EXISTS {table}_cache_trigger ON {table};",
                bot_update=True,
            )
            await self.db.execute(
                f"""
                CREATE TRIGGER {table}_cache_trigger
                AFTER INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION notify_cache_invalidate();
                """,
                bot_update=True,
            )

        db_log.info("Ensured database tables & listeners")

    async def handle_cache_invalidation(self, conn, pid, channel, payload):
        try:
            data = json.loads(payload)
            table = data.get("table")

            if table == "guilds":
                await self.cache.guilds.delete(data["id"])
            elif table == "members":
                await self.cache.members.delete(
                    f"{data['guild_id']}:{data['member_id']}"
                )
            elif table == "users":
                await self.cache.users.delete(data["id"])
            elif table == "configuration":
                await self.cache.config.delete("config")
        except Exception as e:
            db_log.error(f"Error handling cache invalidation: {e}")

    # Guild
    async def get_guild_data(self, guild_id: int) -> dict:
        cached = await self.cache.guilds.get(guild_id)
        if cached is not None:
            return cached

        row = await self.db.fetchrow("SELECT data FROM guilds WHERE id=$1", guild_id)
        if row:
            data = (
                row["data"]
                if isinstance(row["data"], dict)
                else json.loads(row["data"])
            )
        else:
            data = {}
            await self.db.execute(
                "INSERT INTO guilds (id, data) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                guild_id,
                json.dumps(data),
                bot_update=True,
            )
        await self.cache.guilds.set(str(guild_id), data)
        return data

    async def set_guild_data(self, guild_id: int, data: dict):
        await self.db.execute(
            "INSERT INTO guilds (id, data) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET data=$2",
            guild_id,
            json.dumps(data),
            bot_update=True,
        )
        await self.cache.guilds.set(str(guild_id), data)

    # Member
    async def get_member_data(self, guild_id: int, member_id: int) -> dict:
        cache_key = f"{guild_id}:{member_id}"
        cached = await self.cache.members.get(cache_key)
        if cached is not None:
            return cached

        row = await self.db.fetchrow(
            "SELECT data FROM members WHERE guild_id=$1 AND member_id=$2",
            guild_id,
            member_id,
        )
        if row:
            data = (
                row["data"]
                if isinstance(row["data"], dict)
                else json.loads(row["data"])
            )
        else:
            data = {}
            await self.db.execute(
                "INSERT INTO members (guild_id, member_id, data) VALUES ($1, $2, $3) ON CONFLICT (guild_id, member_id) DO NOTHING",
                guild_id,
                member_id,
                json.dumps(data),
                bot_update=True,
            )
        await self.cache.members.set(cache_key, data)
        return data

    async def set_member_data(self, guild_id: int, member_id: int, data: dict):
        cache_key = f"{guild_id}:{member_id}"
        await self.db.execute(
            "INSERT INTO members (guild_id, member_id, data) VALUES ($1, $2, $3) ON CONFLICT (guild_id, member_id) DO UPDATE SET data=$3",
            guild_id,
            member_id,
            json.dumps(data),
            bot_update=True,
        )
        await self.cache.members.set(cache_key, data)

    # User
    async def get_user_data(self, user_id: int) -> dict:
        cached = await self.cache.users.get(user_id)
        if cached is not None:
            return cached

        row = await self.db.fetchrow("SELECT data FROM users WHERE id=$1", user_id)
        if row:
            data = (
                row["data"]
                if isinstance(row["data"], dict)
                else json.loads(row["data"])
            )
        else:
            data = {}
            await self.db.execute(
                "INSERT INTO users (id, data) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                user_id,
                json.dumps(data),
                bot_update=True,
            )
        await self.cache.users.set(str(user_id), data)
        return data

    async def set_user_data(self, user_id: int, data: dict):
        await self.db.execute(
            "INSERT INTO users (id, data) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET data=$2",
            user_id,
            json.dumps(data),
            bot_update=True,
        )
        await self.cache.users.set(str(user_id), data)

    # Configuration
    async def get_configuration(self) -> dict:
        cached = await self.cache.config.get("config")
        if cached is not None:
            return cached

        row = await self.db.fetchrow("SELECT data FROM configuration WHERE active=TRUE")
        if row:
            data = (
                row["data"]
                if isinstance(row["data"], dict)
                else json.loads(row["data"])
            )
        else:
            data = {}
            await self.db.execute(
                "INSERT INTO configuration (active, data) VALUES (TRUE, $1) ON CONFLICT (active) DO NOTHING",
                json.dumps(data),
                bot_update=True,
            )
        await self.cache.config.set("config", data)
        return data

    async def set_configuration(self, data: dict):
        await self.db.execute(
            "INSERT INTO configuration (active, data) VALUES (TRUE, $1) ON CONFLICT (active) DO UPDATE SET data=$1",
            json.dumps(data),
            bot_update=True,
        )
        await self.cache.config.set("config", data)

    # Delete / clear helpers
    async def delete_guild_data(self, guild_id: int):
        await self.db.execute(
            "DELETE FROM guilds WHERE id=$1", guild_id, bot_update=True
        )
        await self.cache.guilds.delete(str(guild_id))

    async def delete_member_data(self, guild_id: int, member_id: int):
        await self.db.execute(
            "DELETE FROM members WHERE guild_id=$1 AND member_id=$2",
            guild_id,
            member_id,
            bot_update=True,
        )
        await self.cache.members.delete(f"{guild_id}:{member_id}")

    async def deep_delete_member_data(self, member_id: int):
        await self.db.execute(
            "DELETE FROM members WHERE member_id=$1", member_id, bot_update=True
        )

        member_str = f":{member_id}"
        await self.cache.members.delete_pattern(member_str)

    async def delete_user_data(self, user_id: int):
        await self.db.execute("DELETE FROM users WHERE id=$1", user_id, bot_update=True)
        await self.cache.users.delete(str(user_id))

    async def clear_cache(self):
        await self.cache.clear_all()


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            intents=intents,
            command_prefix=self.get_prefix,
            help_command=None,
            case_insensitive=True,
            owner_ids=[988623277326991440],
        )

        self.db = Database()
        self.cache = BotCache()
        self.dbf = DatabaseFunctions(self.db, self.cache)
        self._fallback_prefix = _fallback_prefix
        self.bp = "•"

        self.add_check(self.guild_whitelist_check)

        async def load_cogs():
            for root, _, files in os.walk("cogs"):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        rel_path = os.path.relpath(os.path.join(root, file), ".")
                        module = rel_path.replace(os.sep, ".")[:-3]
                        try:
                            await self.load_extension(module)
                            cog_log.info(f"Loaded {module}")
                        except Exception as err:
                            cog_log.error(f"Failed to load {module}: {err}")

        self.load_cogs = load_cogs

    async def guild_whitelist_check(self, ctx: commands.Context):
        if not ctx.guild:
            return False

        config = await self.dbf.get_configuration()
        whitelisted_guilds = config.get("Whitelisted_Guilds", [])

        if ctx.guild.id in whitelisted_guilds:
            return True
        return False

    async def get_prefix(self, message: discord.Message):
        if not message.guild:
            return commands.when_mentioned_or(_fallback_prefix)(self, message)

        prefix = None
        try:
            data = await self.dbf.get_guild_data(message.guild.id)
            config = data.get("Configuration", {})
            prefix = config.get("Prefix", self._fallback_prefix)
        except Exception:
            prefix = _fallback_prefix

        if not prefix:
            prefix = _fallback_prefix

        return commands.when_mentioned_or(prefix)(self, message)

    async def get_raw_prefix(self, message: discord.Message) -> str:
        if not message.guild:
            return self._fallback_prefix

        try:
            data = await self.dbf.get_guild_data(message.guild.id)
            config = data.get("Configuration", {})
            prefix = config.get("Prefix")
            if isinstance(prefix, str) and prefix.strip():
                return prefix
        except Exception:
            pass

        return self._fallback_prefix

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        prefix = await self.get_raw_prefix(message)
        content = message.content

        if not content.startswith(prefix):
            return

        invoked = content[len(prefix) :].split(" ")[0].lower()

        guild_data = await self.dbf.get_guild_data(guild_id=message.guild.id)
        guild_config = guild_data.get("Configuration", {})
        guild_aliases = guild_config.get("Command_Aliases", {})

        if invoked in guild_aliases:
            real = guild_aliases[invoked]
            content = content.replace(prefix + invoked, prefix + real, 1)
            message.content = content

        await self.process_commands(message)

    async def setup_hook(self):
        log.info("Connecting to database...")
        await self.db.connect()
        await self.dbf.init_tables()
        await self.db.start_listener(self.dbf.handle_cache_invalidation)
        log.info("Loading cogs...")
        await self.load_cogs()

    async def close(self):
        log.info("Shutting down...")
        await self.db.close()
        await super().close()

    async def on_ready(self):
        log.info(f"Logged in as {self.user.name}")

        config: dict = await self.dbf.get_configuration()
        status_data: dict = config.get("Statuses", {})

        statuses: list = status_data.get("List", ["i listen to esdeekid and fakemink"])
        settings: dict = status_data.get("Configuration", {})

        randomized: bool = settings.get("Randomized", False)
        loop_enabled: bool = settings.get("LoopingEnabled", True)
        current_status: str = status_data.get("Status")

        if not loop_enabled and current_status:
            status_text = current_status
        elif statuses:
            status_text = random.choice(statuses) if randomized else statuses[0]
        else:
            status_text = None

        if status_text:
            await self.change_presence(
                activity=discord.CustomActivity(name=status_text)
            )


async def main():
    bot = Bot()
    log.info("Starting bot...")
    await bot.start(_token)


if __name__ == "__main__":
    asyncio.run(main())
