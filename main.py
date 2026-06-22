import sys
from pathlib import Path

# 确保 AstrBot 加载插件时能从插件根目录导入 src 包
sys.path.insert(0, str(Path(__file__).parent))

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, StarTools
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.components import At

from src.data.boss_data import BossData
from src.data.chengjiu_data import ChengjiuData
from src.data.exploration_data import ExplorationData
from src.data.item_data import ItemCatalog
from src.data.level_data import LevelData
from src.data.linggen_data import LinggenData
from src.data.occupation_data import OccupationData
from src.data.sect_data import SectData
from src.data.shitu_data import ShituData, ShituShopData
from src.data.shop_data import ShopData
from src.data.tianjiao_data import TianjiaoData
from src.handlers.command_handler import XiuxianCommandHandler
from src.services.battle_service import BattleService
from src.services.boss_service import BossService
from src.services.breakthrough_service import BreakthroughService
from src.services.checkin_service import CheckinService
from src.services.chengjiu_service import ChengjiuService
from src.services.cultivation_service import CultivationService
from src.services.daily_task_service import DailyTaskService
from src.services.demon_service import DemonService
from src.services.exploration_service import ExplorationService
from src.services.admin_service import AdminService
from src.services.auction_service import AuctionService
from src.services.daolv_service import DaolvService
from src.services.exchange_service import ExchangeService
from src.services.gongfa_service import GongfaService
from src.services.inner_world_service import InnerWorldService
from src.services.inventory_service import InventoryService
from src.services.lifespan_service import LifespanService
from src.services.linggen_service import LinggenService
from src.services.pata_service import PataService
from src.services.team_boss_service import TeamBossService
from src.services.xiangu_jinshi_service import XianguJinshiService
from src.services.zhutianjing_service import ZhutianjingService
from src.services.looting_service import LootingService
from src.services.occupation_service import OccupationService
from src.services.player_service import PlayerService
from src.services.ranking_service import RankingService
from src.services.reincarnation_service import ReincarnationService
from src.services.sect_service import SectService
from src.services.shitu_service import ShituService
from src.services.smallworld_service import SmallworldService
from src.services.state_service import StateService
from src.services.tiandibang_service import TiandibangService
from src.services.tianjiao_service import TianjiaoService
from src.services.yuanshen_service import YuanshenService


class AstrBotAdapter:
    """将 AstrMessageEvent 包装成 handler 需要的适配器接口。"""

    def __init__(self, event: AstrMessageEvent):
        self.event = event

    async def get_user_id(self) -> str:
        return self.event.get_sender_id()

    async def get_group_id(self) -> str | None:
        return self.event.get_group_id()

    async def get_at_users(self) -> list[str]:
        """获取消息中 @ 的用户 ID 列表（过滤掉 @全体）。"""
        users: list[str] = []
        for comp in self.event.get_messages():
            if isinstance(comp, At) and str(comp.qq) != "all":
                users.append(str(comp.qq))
        return users

    async def reply_text(self, text: str) -> None:
        self.event.set_result(self.event.plain_result(text))


class ZhutianXiuxianPlugin(Star):
    """诸天万界修仙：将 Yunzai 平台修仙插件移植到 AstrBot。"""

    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config or AstrBotConfig({})
        data_dir = StarTools.get_data_dir("astrbot_plugin_zhutianxiuxian")
        self.player_service = PlayerService(data_dir=data_dir)
        self.state_service = StateService(data_dir=data_dir)
        self.checkin_service = CheckinService(
            player_service=self.player_service,
            state_service=self.state_service,
        )
        self.level_data = LevelData(data_dir=data_dir)
        self.occupation_data = OccupationData(data_dir=data_dir)
        self.linggen_data = LinggenData(data_dir=data_dir)
        self.item_catalog = ItemCatalog(data_dir=data_dir)
        self.tianjiao_data = TianjiaoData(data_dir=data_dir)
        self.exploration_data = ExplorationData(data_dir=data_dir)
        self.sect_data = SectData(data_dir=data_dir)
        self.shop_data = ShopData(data_dir=data_dir)
        self.shitu_data = ShituData(data_dir=data_dir)
        self.shitu_shop_data = ShituShopData(data_dir=data_dir)
        self.chengjiu_data = ChengjiuData(data_dir=data_dir)
        self.breakthrough_service = BreakthroughService(
            player_service=self.player_service,
            level_data=self.level_data,
        )
        self.cultivation_service = CultivationService(
            player_service=self.player_service,
            state_service=self.state_service,
        )
        self.tianjiao_service = TianjiaoService(
            tianjiao_data=self.tianjiao_data,
            state_service=self.state_service,
            player_service=self.player_service,
        )
        self.exploration_service = ExplorationService(
            player_service=self.player_service,
            state_service=self.state_service,
            exploration_data=self.exploration_data,
        )
        self.battle_service = BattleService(
            player_service=self.player_service,
            level_data=self.level_data,
            state_service=self.state_service,
            data_dir=data_dir,
        )
        self.boss_data = BossData(data_dir=data_dir)
        self.boss_service = BossService(
            battle_service=self.battle_service,
            player_service=self.player_service,
            state_service=self.state_service,
            boss_data=self.boss_data,
            data_dir=data_dir,
        )
        self.ranking_service = RankingService(
            player_service=self.player_service,
            data_dir=data_dir,
            level_data=self.level_data,
        )
        self.inventory_service = InventoryService(
            player_service=self.player_service,
        )
        self.tiandibang_service = TiandibangService(
            player_service=self.player_service,
            battle_service=self.battle_service,
            inventory_service=self.inventory_service,
            state_service=self.state_service,
            data_dir=data_dir,
            item_catalog=self.item_catalog,
        )
        self.lifespan_service = LifespanService(
            player_service=self.player_service,
            state_service=self.state_service,
        )
        self.yuanshen_service = YuanshenService(
            player_service=self.player_service,
            level_data=self.level_data,
            state_service=self.state_service,
        )
        self.inner_world_service = InnerWorldService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            item_catalog=self.item_catalog,
            data_dir=data_dir,
        )
        self.xiangu_jinshi_service = XianguJinshiService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            level_data=self.level_data,
        )
        self.auction_service = AuctionService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            data_dir=data_dir,
        )
        self.exchange_service = ExchangeService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            item_catalog=self.item_catalog,
            data_dir=data_dir,
        )
        self.daolv_service = DaolvService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            data_dir=data_dir,
        )
        self.team_boss_service = TeamBossService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            battle_service=self.battle_service,
            data_dir=data_dir,
        )
        self.pata_service = PataService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            data_dir=data_dir,
        )
        self.zhutianjing_service = ZhutianjingService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            data_dir=data_dir,
        )
        self.admin_service = AdminService(
            player_service=self.player_service,
            data_dir=data_dir,
        )
        self.gongfa_service = GongfaService(
            player_service=self.player_service,
            item_catalog=self.item_catalog,
        )
        self.occupation_service = OccupationService(
            player_service=self.player_service,
            state_service=self.state_service,
            inventory_service=self.inventory_service,
            occupation_data=self.occupation_data,
        )
        self.linggen_service = LinggenService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            state_service=self.state_service,
            linggen_data=self.linggen_data,
        )
        self.sect_service = SectService(
            player_service=self.player_service,
            state_service=self.state_service,
            sect_data=self.sect_data,
        )
        self.daily_task_service = DailyTaskService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            state_service=self.state_service,
        )
        self.demon_service = DemonService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            state_service=self.state_service,
        )
        self.looting_service = LootingService(
            player_service=self.player_service,
            state_service=self.state_service,
            inventory_service=self.inventory_service,
            shop_data=self.shop_data,
        )
        self.reincarnation_service = ReincarnationService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            state_service=self.state_service,
        )
        self.shitu_service = ShituService(
            player_service=self.player_service,
            state_service=self.state_service,
            inventory_service=self.inventory_service,
            shitu_data=self.shitu_data,
            shop_data=self.shitu_shop_data,
        )
        self.smallworld_service = SmallworldService(
            player_service=self.player_service,
            inventory_service=self.inventory_service,
            data_dir=data_dir,
        )
        self.chengjiu_service = ChengjiuService(
            player_service=self.player_service,
            chengjiu_data=self.chengjiu_data,
        )
        master_ids = set(str(uid) for uid in (self.config.get("MASTER_IDS", []) or []))
        self.command_handler = XiuxianCommandHandler(
            player_service=self.player_service,
            checkin_service=self.checkin_service,
            level_data=self.level_data,
            breakthrough_service=self.breakthrough_service,
            cultivation_service=self.cultivation_service,
            occupation_data=self.occupation_data,
            item_catalog=self.item_catalog,
            tianjiao_service=self.tianjiao_service,
            exploration_service=self.exploration_service,
            exploration_data=self.exploration_data,
            battle_service=self.battle_service,
            boss_service=self.boss_service,
            boss_data=self.boss_data,
            ranking_service=self.ranking_service,
            lifespan_service=self.lifespan_service,
            yuanshen_service=self.yuanshen_service,
            inventory_service=self.inventory_service,
            gongfa_service=self.gongfa_service,
            inner_world_service=self.inner_world_service,
            xiangu_jinshi_service=self.xiangu_jinshi_service,
            auction_service=self.auction_service,
            exchange_service=self.exchange_service,
            daolv_service=self.daolv_service,
            team_boss_service=self.team_boss_service,
            pata_service=self.pata_service,
            zhutianjing_service=self.zhutianjing_service,
            admin_service=self.admin_service,
            occupation_service=self.occupation_service,
            linggen_service=self.linggen_service,
            sect_service=self.sect_service,
            daily_task_service=self.daily_task_service,
            demon_service=self.demon_service,
            looting_service=self.looting_service,
            reincarnation_service=self.reincarnation_service,
            shitu_service=self.shitu_service,
            smallworld_service=self.smallworld_service,
            tiandibang_service=self.tiandibang_service,
            sect_data=self.sect_data,
            shop_data=self.shop_data,
            shitu_data=self.shitu_data,
            shitu_shop_data=self.shitu_shop_data,
            chengjiu_service=self.chengjiu_service,
            master_ids=master_ids,
        )
        logger.info("[诸天万界修仙] 插件已初始化")

    async def initialize(self):
        """AstrBot 加载完成后调用，可用于启动定时任务、连接数据库等。"""
        initial_admins = self.config.get("INITIAL_ADMINS", []) or []
        for uid in initial_admins:
            await self.admin_service.add_admin(str(uid))
        logger.info("[诸天万界修仙] 插件已加载")

    async def terminate(self):
        """AstrBot 卸载时调用，可用于清理定时任务、关闭连接等。"""
        logger.info("[诸天万界修仙] 插件已卸载")

    @filter.command("刷新信息", "刷新玩家缺失字段与衍生属性")
    async def refresh_info(self, event: AstrMessageEvent):
        """刷新玩家缺失字段与衍生属性"""
        await self._dispatch(event)

    @filter.command("修仙帮助", "显示修仙指令帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示修仙指令帮助"""
        await self._dispatch(event)

    @filter.command("踏入仙途", "创建修仙角色")
    async def start_cultivation(self, event: AstrMessageEvent):
        """创建修仙角色"""
        await self._dispatch(event)

    @filter.command("我的练气", "查看角色信息")
    async def show_player(self, event: AstrMessageEvent):
        """查看角色信息"""
        await self._dispatch(event)

    @filter.command("我的", "查看完整角色信息")
    async def show_full_info(self, event: AstrMessageEvent):
        """查看完整角色信息"""
        await self._dispatch(event)

    @filter.command("我的炼体", "查看炼体信息")
    async def show_physique(self, event: AstrMessageEvent):
        """查看炼体信息"""
        await self._dispatch(event)

    @filter.command("修仙签到", "每日签到")
    async def daily_checkin(self, event: AstrMessageEvent):
        """每日签到"""
        await self._dispatch(event)

    @filter.command("修仙状态", "查看当前修仙动作状态")
    async def show_status(self, event: AstrMessageEvent):
        """查看当前修仙动作状态"""
        await self._dispatch(event)

    @filter.command("练气境界", "查看练气境界表")
    async def show_cultivation_levels(self, event: AstrMessageEvent):
        """查看练气境界表"""
        await self._dispatch(event)

    @filter.command("炼体境界", "查看炼体境界表")
    async def show_physique_levels(self, event: AstrMessageEvent):
        """查看炼体境界表"""
        await self._dispatch(event)

    @filter.command("秘境体系", "查看秘境体系境界表")
    async def show_mijing_levels(self, event: AstrMessageEvent):
        """查看秘境体系境界表"""
        await self._dispatch(event)

    @filter.command("仙古今世法", "查看仙古今世法境界表")
    async def show_xiangu_levels(self, event: AstrMessageEvent):
        """查看仙古今世法境界表"""
        await self._dispatch(event)

    @filter.command("职业等级", "查看职业列表")
    async def show_occupation_levels(self, event: AstrMessageEvent):
        """查看职业列表"""
        await self._dispatch(event)

    @filter.command("装备楼", "查看装备列表")
    async def show_equipment_catalog(self, event: AstrMessageEvent):
        """查看装备列表"""
        await self._dispatch(event)

    @filter.command("丹药楼", "查看丹药列表")
    async def show_pill_catalog(self, event: AstrMessageEvent):
        """查看丹药列表"""
        await self._dispatch(event)

    @filter.command("道具楼", "查看道具列表")
    async def show_item_catalog(self, event: AstrMessageEvent):
        """查看道具列表"""
        await self._dispatch(event)

    @filter.command("功法楼", "查看功法列表")
    async def show_gongfa_catalog(self, event: AstrMessageEvent):
        """查看功法列表"""
        await self._dispatch(event)

    @filter.command("草药楼", "查看草药列表")
    async def show_herb_catalog(self, event: AstrMessageEvent):
        """查看草药列表"""
        await self._dispatch(event)

    @filter.command("食材楼", "查看食材列表")
    async def show_food_catalog(self, event: AstrMessageEvent):
        """查看食材列表"""
        await self._dispatch(event)

    @filter.command("盒子楼", "查看盒子列表")
    async def show_box_catalog(self, event: AstrMessageEvent):
        """查看盒子列表"""
        await self._dispatch(event)

    @filter.command("材料楼", "查看材料列表")
    async def show_material_catalog(self, event: AstrMessageEvent):
        """查看材料列表"""
        await self._dispatch(event)

    @filter.command("仙宠楼", "查看仙宠列表")
    async def show_pet_catalog(self, event: AstrMessageEvent):
        """查看仙宠列表"""
        await self._dispatch(event)

    @filter.command("口粮楼", "查看仙宠口粮列表")
    async def show_pet_food_catalog(self, event: AstrMessageEvent):
        """查看仙宠口粮列表"""
        await self._dispatch(event)

    @filter.command("宝石楼", "查看宝石列表")
    async def show_gem_catalog(self, event: AstrMessageEvent):
        """查看宝石列表"""
        await self._dispatch(event)

    @filter.command("一键突破", "一键连续练气突破")
    async def auto_breakthrough(self, event: AstrMessageEvent):
        """一键连续练气突破"""
        await self._dispatch(event)

    @filter.command("一键破体", "一键连续炼体突破")
    async def auto_physique_breakthrough(self, event: AstrMessageEvent):
        """一键连续炼体突破"""
        await self._dispatch(event)

    @filter.command("突破", "练气境界突破")
    async def breakthrough(self, event: AstrMessageEvent):
        """练气境界突破"""
        await self._dispatch(event)

    @filter.command("幸运突破", "消耗灵石的幸运练气突破")
    async def lucky_breakthrough(self, event: AstrMessageEvent):
        """消耗灵石的幸运练气突破"""
        await self._dispatch(event)

    @filter.command("破体", "炼体境界突破")
    async def physique_breakthrough(self, event: AstrMessageEvent):
        """炼体境界突破"""
        await self._dispatch(event)

    @filter.command("幸运破体", "消耗灵石的幸运炼体突破")
    async def lucky_physique_breakthrough(self, event: AstrMessageEvent):
        """消耗灵石的幸运炼体突破"""
        await self._dispatch(event)

    @filter.command("设置性别", "设置角色性别")
    async def set_sex(self, event: AstrMessageEvent):
        """设置角色性别"""
        await self._dispatch(event)

    @filter.command("改名", "修改角色道号")
    async def rename(self, event: AstrMessageEvent):
        """修改角色道号"""
        await self._dispatch(event)

    @filter.command("设置道宣", "设置角色道宣")
    async def set_motto(self, event: AstrMessageEvent):
        """设置角色道宣"""
        await self._dispatch(event)

    @filter.command("闭关", "开始闭关修炼")
    async def start_seclusion(self, event: AstrMessageEvent):
        """开始闭关修炼"""
        await self._dispatch(event)

    @filter.command("出关", "结束闭关结算修为")
    async def end_seclusion(self, event: AstrMessageEvent):
        """结束闭关结算修为"""
        await self._dispatch(event)

    @filter.command("降妖", "开始降妖获取血气")
    async def start_hunt(self, event: AstrMessageEvent):
        """开始降妖获取血气"""
        await self._dispatch(event)

    @filter.command("降妖归来", "结束降妖结算血气")
    async def end_hunt(self, event: AstrMessageEvent):
        """结束降妖结算血气"""
        await self._dispatch(event)

    @filter.command("天骄列表", "查看位面天骄列表")
    async def show_tianjiao_list(self, event: AstrMessageEvent):
        """查看位面天骄列表"""
        await self._dispatch(event)

    @filter.command("天骄状态", "查看天骄状态")
    async def show_tianjiao_status(self, event: AstrMessageEvent):
        """查看天骄状态"""
        await self._dispatch(event)

    @filter.command("讨伐天骄", "讨伐位面天骄")
    async def challenge_tianjiao(self, event: AstrMessageEvent):
        """讨伐位面天骄"""
        await self._dispatch(event)

    @filter.command("天骄贡献榜", "查看天骄伤害贡献榜")
    async def show_tianjiao_damage_list(self, event: AstrMessageEvent):
        """查看天骄伤害贡献榜"""
        await self._dispatch(event)

    @filter.command("开启天骄", "初始化天骄状态（管理员）")
    async def init_tianjiao(self, event: AstrMessageEvent):
        """初始化天骄状态（管理员）"""
        await self._dispatch(event)

    @filter.command("关闭天骄", "关闭并重置天骄状态（管理员）")
    async def close_tianjiao(self, event: AstrMessageEvent):
        """关闭并重置天骄状态（管理员）"""
        await self._dispatch(event)

    @filter.command("秘境", "查看秘境列表")
    async def show_secret_places(self, event: AstrMessageEvent):
        """查看秘境列表"""
        await self._dispatch(event)

    @filter.command("降临秘境", "降临秘境开始探索")
    async def start_secret_place(self, event: AstrMessageEvent):
        """降临秘境开始探索"""
        await self._dispatch(event)

    @filter.command("禁地", "查看禁地列表")
    async def show_forbidden_areas(self, event: AstrMessageEvent):
        """查看禁地列表"""
        await self._dispatch(event)

    @filter.command("前往禁地", "前往禁地开始探索")
    async def start_forbidden_area(self, event: AstrMessageEvent):
        """前往禁地开始探索"""
        await self._dispatch(event)

    @filter.command("仙府", "查看限定仙府列表")
    async def show_time_places(self, event: AstrMessageEvent):
        """查看限定仙府列表"""
        await self._dispatch(event)

    @filter.command("探索仙府", "探索限定仙府")
    async def start_time_place(self, event: AstrMessageEvent):
        """探索限定仙府"""
        await self._dispatch(event)

    @filter.command("仙境", "查看仙境列表")
    async def show_fairy_realms(self, event: AstrMessageEvent):
        """查看仙境列表"""
        await self._dispatch(event)

    @filter.command("镇守仙境", "镇守仙境")
    async def start_fairy_realm(self, event: AstrMessageEvent):
        """镇守仙境"""
        await self._dispatch(event)

    @filter.command("逃离", "逃离当前探索")
    async def give_up(self, event: AstrMessageEvent):
        """逃离当前探索"""
        await self._dispatch(event)

    @filter.command("副本掉落", "查看副本掉落")
    async def show_dungeon_drop(self, event: AstrMessageEvent):
        """查看副本掉落"""
        await self._dispatch(event)

    @filter.command("打劫", "打劫指定玩家")
    async def rob_player(self, event: AstrMessageEvent):
        """打劫指定玩家"""
        await self._dispatch(event)

    @filter.command("比武", "与指定玩家比武")
    async def duel_player(self, event: AstrMessageEvent):
        """与指定玩家比武"""
        await self._dispatch(event)

    @filter.command("开启妖王", "初始化世界妖王")
    async def init_boss(self, event: AstrMessageEvent):
        """初始化世界妖王"""
        await self._dispatch(event)

    @filter.command("关闭妖王", "关闭世界妖王")
    async def close_boss(self, event: AstrMessageEvent):
        """关闭世界妖王"""
        await self._dispatch(event)

    @filter.command("妖王状态", "查看妖王状态")
    async def show_boss_status(self, event: AstrMessageEvent):
        """查看妖王状态"""
        await self._dispatch(event)

    @filter.command("妖王贡献榜", "查看妖王伤害贡献榜")
    async def show_boss_damage_list(self, event: AstrMessageEvent):
        """查看妖王伤害贡献榜"""
        await self._dispatch(event)

    @filter.command("讨伐妖王", "讨伐世界妖王")
    async def challenge_boss(self, event: AstrMessageEvent):
        """讨伐世界妖王"""
        await self._dispatch(event)

    @filter.command("魔道榜", "查看魔道榜")
    async def show_modao_ranking(self, event: AstrMessageEvent):
        """查看魔道榜"""
        await self._dispatch(event)

    @filter.command("强化榜", "查看强化榜")
    async def show_enhance_ranking(self, event: AstrMessageEvent):
        """查看强化榜"""
        await self._dispatch(event)

    @filter.command("天榜", "查看天榜（修为排行）")
    async def show_exp_ranking(self, event: AstrMessageEvent):
        """查看天榜（修为排行）"""
        await self._dispatch(event)

    @filter.command("灵榜", "查看灵榜（灵石排行）")
    async def show_spirit_stones_ranking(self, event: AstrMessageEvent):
        """查看灵榜（灵石排行）"""
        await self._dispatch(event)

    @filter.command("封神榜", "查看封神榜")
    async def show_fengshen_ranking(self, event: AstrMessageEvent):
        """查看封神榜"""
        await self._dispatch(event)

    @filter.command("遮天榜", "查看遮天榜")
    async def show_zhetian_ranking(self, event: AstrMessageEvent):
        """查看遮天榜"""
        await self._dispatch(event)

    @filter.command("完美世界榜", "查看完美世界榜")
    async def show_xiangu_ranking(self, event: AstrMessageEvent):
        """查看完美世界榜"""
        await self._dispatch(event)

    @filter.command("至尊榜", "查看至尊榜")
    async def show_zhizun_ranking(self, event: AstrMessageEvent):
        """查看至尊榜"""
        await self._dispatch(event)

    @filter.command("镇妖塔榜", "查看镇妖塔榜")
    async def show_zhenyao_ranking(self, event: AstrMessageEvent):
        """查看镇妖塔榜"""
        await self._dispatch(event)

    @filter.command("神魄榜", "查看神魄榜")
    async def show_shenpo_ranking(self, event: AstrMessageEvent):
        """查看神魄榜"""
        await self._dispatch(event)

    # ---------- 天地榜 ----------

    @filter.command("报名比赛", "报名参加天地榜")
    async def tiandibang_register(self, event: AstrMessageEvent):
        """报名参加天地榜"""
        await self._dispatch(event)

    @filter.command("更新属性", "更新天地榜属性快照")
    async def tiandibang_update(self, event: AstrMessageEvent):
        """更新天地榜属性快照"""
        await self._dispatch(event)

    @filter.command("天地榜", "查看天地榜及个人排名")
    async def tiandibang_ranking(self, event: AstrMessageEvent):
        """查看天地榜及个人排名"""
        await self._dispatch(event)

    @filter.command("比试", "天地榜比试")
    async def tiandibang_challenge(self, event: AstrMessageEvent):
        """天地榜比试"""
        await self._dispatch(event)

    @filter.command("天地堂", "查看天地堂商品")
    async def tiandibang_shop(self, event: AstrMessageEvent):
        """查看天地堂商品"""
        await self._dispatch(event)

    @filter.command("积分兑换", "天地榜积分兑换物品")
    async def tiandibang_exchange(self, event: AstrMessageEvent):
        """天地榜积分兑换物品"""
        await self._dispatch(event)

    @filter.command("结算天地榜奖励", "结算天地榜奖励（管理员）")
    async def tiandibang_settle(self, event: AstrMessageEvent):
        """结算天地榜奖励（管理员）"""
        await self._dispatch(event)

    @filter.command("清空积分", "清空天地榜积分（管理员）")
    async def tiandibang_reset(self, event: AstrMessageEvent):
        """清空天地榜积分（管理员）"""
        await self._dispatch(event)

    # ---------- 小世界 ----------
    @filter.command("开辟小世界", "开辟小世界")
    async def smallworld_create(self, event: AstrMessageEvent):
        """开辟小世界"""
        await self._dispatch(event)

    @filter.command("演化小世界", "演化小世界")
    async def smallworld_upgrade(self, event: AstrMessageEvent):
        """演化小世界"""
        await self._dispatch(event)

    @filter.command("我的小世界", "查看我的小世界")
    async def smallworld_view(self, event: AstrMessageEvent):
        """查看我的小世界"""
        await self._dispatch(event)

    @filter.command("将分身化入小世界", "将分身化入小世界")
    async def smallworld_avatar(self, event: AstrMessageEvent):
        """将分身化入小世界"""
        await self._dispatch(event)

    @filter.command("收获小世界资源", "收获小世界资源")
    async def smallworld_harvest(self, event: AstrMessageEvent):
        """收获小世界资源"""
        await self._dispatch(event)

    @filter.command("种植指南", "查看小世界种植指南")
    async def smallworld_planting_help(self, event: AstrMessageEvent):
        """查看小世界种植指南"""
        await self._dispatch(event)

    @filter.command("小世界栽种", "在小世界栽种神药")
    async def smallworld_plant(self, event: AstrMessageEvent):
        """在小世界栽种神药"""
        await self._dispatch(event)

    @filter.command("浇灌小世界作物", "使用乾坤造化瓶浇灌全部作物")
    async def smallworld_water_all(self, event: AstrMessageEvent):
        """使用乾坤造化瓶浇灌全部作物"""
        await self._dispatch(event)

    @filter.command("使用", "使用道具浇灌作物或创造环境")
    async def smallworld_use_item(self, event: AstrMessageEvent):
        """使用道具浇灌作物或创造环境"""
        await self._dispatch(event)

    @filter.command("催熟小世界作物", "管理员催熟小世界作物")
    async def smallworld_force_ripen(self, event: AstrMessageEvent):
        """管理员催熟小世界作物"""
        await self._dispatch(event)

    @filter.command("查看寿元", "查看当前寿元")
    async def show_lifespan(self, event: AstrMessageEvent):
        """查看当前寿元"""
        await self._dispatch(event)

    @filter.command("执行寿元流逝", "手动执行寿元流逝（管理员）")
    async def reduce_lifespan_manual(self, event: AstrMessageEvent):
        """手动执行寿元流逝（管理员）"""
        await self._dispatch(event)

    @filter.command("我的元神", "查看元神状态")
    async def show_yuanshen(self, event: AstrMessageEvent):
        """查看元神状态"""
        await self._dispatch(event)

    @filter.command("凝练元神", "凝练/升级元神")
    async def condense_yuanshen(self, event: AstrMessageEvent):
        """凝练/升级元神"""
        await self._dispatch(event)

    @filter.command("开启内景地", "开启内景地")
    async def open_neijing(self, event: AstrMessageEvent):
        """开启内景地"""
        await self._dispatch(event)

    @filter.command("进入内景地", "进入内景地")
    async def enter_neijing(self, event: AstrMessageEvent):
        """进入内景地"""
        await self._dispatch(event)

    @filter.command("内景地修炼", "批量内景地修炼")
    async def neijing_batch(self, event: AstrMessageEvent):
        """批量内景地修炼"""
        await self._dispatch(event)

    @filter.command("开辟内景地空间", "开辟内景地空间仓库")
    async def open_inner_world(self, event: AstrMessageEvent):
        """开辟内景地空间仓库"""
        await self._dispatch(event)

    @filter.command("查看内景地", "查看内景地空间仓库")
    async def view_inner_world(self, event: AstrMessageEvent):
        """查看内景地空间仓库"""
        await self._dispatch(event)

    @filter.command("升级内景地空间", "升级内景地空间仓库")
    async def upgrade_inner_world(self, event: AstrMessageEvent):
        """升级内景地空间仓库"""
        await self._dispatch(event)

    @filter.command("存入", "存入物品到内景地空间")
    async def store_inner_world(self, event: AstrMessageEvent):
        """存入物品到内景地空间"""
        await self._dispatch(event)

    @filter.command("取出", "从内景地空间取出物品")
    async def take_inner_world(self, event: AstrMessageEvent):
        """从内景地空间取出物品"""
        await self._dispatch(event)

    @filter.command("一键存入内景地", "一键存入物品到内景地空间")
    async def store_all_inner_world(self, event: AstrMessageEvent):
        """一键存入物品到内景地空间"""
        await self._dispatch(event)

    @filter.command("一键取出内景地", "一键取出内景地空间物品")
    async def take_all_inner_world(self, event: AstrMessageEvent):
        """一键取出内景地空间物品"""
        await self._dispatch(event)

    @filter.command("冲关", "仙古今世法普通冲关")
    async def xiangu_breakthrough(self, event: AstrMessageEvent):
        """仙古今世法普通冲关"""
        await self._dispatch(event)

    @filter.command("冲关极境", "仙古今世法极境冲关")
    async def xiangu_extreme(self, event: AstrMessageEvent):
        """仙古今世法极境冲关"""
        await self._dispatch(event)

    @filter.command("拍卖", "上架物品到拍卖行")
    async def create_auction(self, event: AstrMessageEvent):
        """上架物品到拍卖行"""
        await self._dispatch(event)

    @filter.command("查看当前拍卖", "查看当前拍卖")
    async def show_auction(self, event: AstrMessageEvent):
        """查看当前拍卖"""
        await self._dispatch(event)

    @filter.command("竞价", "拍卖出价")
    async def bid_auction(self, event: AstrMessageEvent):
        """拍卖出价"""
        await self._dispatch(event)

    @filter.command("交易", "上架物品交易")
    async def exchange_sell(self, event: AstrMessageEvent):
        """上架物品交易"""
        await self._dispatch(event)

    @filter.command("查看交易", "查看交易列表")
    async def show_exchange(self, event: AstrMessageEvent):
        """查看交易列表"""
        await self._dispatch(event)

    @filter.command("购买", "购买交易物品")
    async def exchange_buy(self, event: AstrMessageEvent):
        """购买交易物品"""
        await self._dispatch(event)

    @filter.command("求购", "发布求购信息")
    async def exchange_request(self, event: AstrMessageEvent):
        """发布求购信息"""
        await self._dispatch(event)

    @filter.command("下架", "下架交易挂单")
    async def exchange_remove(self, event: AstrMessageEvent):
        """下架交易挂单"""
        await self._dispatch(event)

    @filter.command("结为道侣", "向指定玩家结为道侣")
    async def propose_daolv(self, event: AstrMessageEvent):
        """向指定玩家结为道侣"""
        await self._dispatch(event)

    @filter.command("同意道侣", "同意道侣请求")
    async def accept_daolv(self, event: AstrMessageEvent):
        """同意道侣请求"""
        await self._dispatch(event)

    @filter.command("拒绝道侣", "拒绝道侣请求")
    async def reject_daolv(self, event: AstrMessageEvent):
        """拒绝道侣请求"""
        await self._dispatch(event)

    @filter.command("我的道侣", "查看道侣信息")
    async def show_daolv(self, event: AstrMessageEvent):
        """查看道侣信息"""
        await self._dispatch(event)

    @filter.command("赠送百合花篮", "赠送百合花篮提升亲密度")
    async def gift_daolv(self, event: AstrMessageEvent):
        """赠送百合花篮提升亲密度"""
        await self._dispatch(event)

    @filter.command("断绝姻缘", "断绝道侣关系")
    async def breakup_daolv(self, event: AstrMessageEvent):
        """断绝道侣关系"""
        await self._dispatch(event)

    @filter.command("开启团本", "开启团队BOSS副本")
    async def create_team_boss(self, event: AstrMessageEvent):
        """开启团队BOSS副本"""
        await self._dispatch(event)

    @filter.command("加入团本", "加入当前团本")
    async def join_team_boss(self, event: AstrMessageEvent):
        """加入当前团本"""
        await self._dispatch(event)

    @filter.command("退出团本", "退出当前团本")
    async def leave_team_boss(self, event: AstrMessageEvent):
        """退出当前团本"""
        await self._dispatch(event)

    @filter.command("攻击团本", "攻击团本BOSS")
    async def attack_team_boss(self, event: AstrMessageEvent):
        """攻击团本BOSS"""
        await self._dispatch(event)

    @filter.command("团本状态", "查看团本状态")
    async def status_team_boss(self, event: AstrMessageEvent):
        """查看团本状态"""
        await self._dispatch(event)

    @filter.command("结算团本", "结算团本奖励")
    async def settle_team_boss(self, event: AstrMessageEvent):
        """结算团本奖励"""
        await self._dispatch(event)

    @filter.command("挑战镇妖塔", "挑战镇妖塔")
    async def challenge_zhenyao(self, event: AstrMessageEvent):
        """挑战镇妖塔"""
        await self._dispatch(event)

    @filter.command("一键镇妖塔", "一键挑战镇妖塔")
    async def auto_challenge_zhenyao(self, event: AstrMessageEvent):
        """一键挑战镇妖塔"""
        await self._dispatch(event)

    @filter.command("我的镇妖塔", "查看镇妖塔进度")
    async def show_zhenyao(self, event: AstrMessageEvent):
        """查看镇妖塔进度"""
        await self._dispatch(event)

    @filter.command("挑战锻神池", "挑战锻神池")
    async def challenge_shenpo(self, event: AstrMessageEvent):
        """挑战锻神池"""
        await self._dispatch(event)

    @filter.command("一键锻神池", "一键挑战锻神池")
    async def auto_challenge_shenpo(self, event: AstrMessageEvent):
        """一键挑战锻神池"""
        await self._dispatch(event)

    @filter.command("我的锻神池", "查看锻神池进度")
    async def show_shenpo(self, event: AstrMessageEvent):
        """查看锻神池进度"""
        await self._dispatch(event)

    @filter.command("穿越诸天镜", "穿越诸天镜")
    async def enter_zhutianjing(self, event: AstrMessageEvent):
        """穿越诸天镜"""
        await self._dispatch(event)

    @filter.command("救赎", "诸天镜救赎")
    async def redeem_zhutianjing(self, event: AstrMessageEvent):
        """诸天镜救赎"""
        await self._dispatch(event)

    @filter.command("魔法少女进阶", "魔法少女进阶")
    async def advance_magic_girl(self, event: AstrMessageEvent):
        """魔法少女进阶"""
        await self._dispatch(event)

    @filter.command("我的诸天镜", "查看诸天镜信息")
    async def show_zhutianjing(self, event: AstrMessageEvent):
        """查看诸天镜信息"""
        await self._dispatch(event)

    @filter.command("库洛牌", "抽取库洛牌")
    async def draw_clow_card(self, event: AstrMessageEvent):
        """抽取库洛牌"""
        await self._dispatch(event)

    @filter.command("备份存档", "备份玩家数据")
    async def backup_data(self, event: AstrMessageEvent):
        """备份玩家数据"""
        await self._dispatch(event)

    @filter.command("恢复备份", "从备份恢复")
    async def restore_backup(self, event: AstrMessageEvent):
        """从备份恢复"""
        await self._dispatch(event)

    @filter.command("管理员加灵石", "管理员给玩家加灵石")
    async def admin_add_spirit_stones(self, event: AstrMessageEvent):
        """管理员给玩家加灵石"""
        await self._dispatch(event)

    @filter.command("管理员加源石", "管理员给玩家加源石")
    async def admin_add_source_stones(self, event: AstrMessageEvent):
        """管理员给玩家加源石"""
        await self._dispatch(event)

    @filter.command("管理员封号", "管理员封号")
    async def admin_ban(self, event: AstrMessageEvent):
        """管理员封号"""
        await self._dispatch(event)

    @filter.command("管理员解封", "管理员解封")
    async def admin_unban(self, event: AstrMessageEvent):
        """管理员解封"""
        await self._dispatch(event)

    @filter.command("设置时代", "设置当前时代")
    async def admin_set_era(self, event: AstrMessageEvent):
        """设置当前时代"""
        await self._dispatch(event)

    @filter.command("下一个时代", "进入下一个时代")
    async def admin_next_era(self, event: AstrMessageEvent):
        """进入下一个时代"""
        await self._dispatch(event)

    @filter.command("纪元", "查看当前纪元")
    async def admin_show_era(self, event: AstrMessageEvent):
        """查看当前纪元"""
        await self._dispatch(event)

    @filter.command("自动任务", "开启/关闭自动任务")
    async def admin_auto_task(self, event: AstrMessageEvent):
        """开启/关闭自动任务"""
        await self._dispatch(event)

    @filter.command("我的纳戒", "查看玩家纳戒")
    async def show_inventory(self, event: AstrMessageEvent):
        """查看玩家纳戒"""
        await self._dispatch(event)

    @filter.command("我的功法", "查看已学功法")
    async def show_gongfa(self, event: AstrMessageEvent):
        """查看已学功法"""
        await self._dispatch(event)

    @filter.command("学习功法", "学习指定功法")
    async def learn_gongfa(self, event: AstrMessageEvent):
        """学习指定功法"""
        await self._dispatch(event)

    @filter.command("我的职业", "查看当前职业信息")
    async def show_occupation(self, event: AstrMessageEvent):
        """查看当前职业信息"""
        await self._dispatch(event)

    @filter.command("转职", "转职为指定职业")
    async def change_occupation(self, event: AstrMessageEvent):
        """转职为指定职业"""
        await self._dispatch(event)

    @filter.command("转换副职", "切换主副职业")
    async def swap_secondary_occupation(self, event: AstrMessageEvent):
        """切换主副职业"""
        await self._dispatch(event)

    @filter.command("猎户转", "猎户专属转职")
    async def change_from_liehu(self, event: AstrMessageEvent):
        """猎户专属转职"""
        await self._dispatch(event)

    @filter.command("采药", "开始采药")
    async def start_herbalism(self, event: AstrMessageEvent):
        """开始采药"""
        await self._dispatch(event)

    @filter.command("结束采药", "结束采药并结算")
    async def end_herbalism(self, event: AstrMessageEvent):
        """结束采药并结算"""
        await self._dispatch(event)

    @filter.command("采矿", "开始采矿")
    async def start_mining(self, event: AstrMessageEvent):
        """开始采矿"""
        await self._dispatch(event)

    @filter.command("结束采矿", "结束采矿并结算")
    async def end_mining(self, event: AstrMessageEvent):
        """结束采矿并结算"""
        await self._dispatch(event)

    @filter.command("狩猎", "开始狩猎")
    async def start_hunting(self, event: AstrMessageEvent):
        """开始狩猎"""
        await self._dispatch(event)

    @filter.command("结束狩猎", "结束狩猎并结算")
    async def end_hunting(self, event: AstrMessageEvent):
        """结束狩猎并结算"""
        await self._dispatch(event)

    @filter.command("寻源", "开始寻源")
    async def start_source_seeking(self, event: AstrMessageEvent):
        """开始寻源"""
        await self._dispatch(event)

    @filter.command("结束寻源", "结束寻源并结算")
    async def end_source_seeking(self, event: AstrMessageEvent):
        """结束寻源并结算"""
        await self._dispatch(event)

    @filter.command("寻脉定源", "开始寻脉定源")
    async def start_source_locking(self, event: AstrMessageEvent):
        """开始寻脉定源"""
        await self._dispatch(event)

    @filter.command("结束寻脉定源", "结束寻脉定源并结算")
    async def end_source_locking(self, event: AstrMessageEvent):
        """结束寻脉定源并结算"""
        await self._dispatch(event)

    @filter.command("地脉引气", "开始地脉引气")
    async def start_earth_breath(self, event: AstrMessageEvent):
        """开始地脉引气"""
        await self._dispatch(event)

    @filter.command("结束地脉引气", "结束地脉引气并结算")
    async def end_earth_breath(self, event: AstrMessageEvent):
        """结束地脉引气并结算"""
        await self._dispatch(event)

    @filter.command("丹药配方", "查看炼丹配方")
    async def show_danfang_recipes(self, event: AstrMessageEvent):
        """查看炼丹配方"""
        await self._dispatch(event)

    @filter.command("符道配方", "查看制符配方")
    async def show_zhizuo_recipes(self, event: AstrMessageEvent):
        """查看制符配方"""
        await self._dispatch(event)

    @filter.command("装备图纸", "查看装备图纸")
    async def show_equipment_blueprints(self, event: AstrMessageEvent):
        """查看装备图纸"""
        await self._dispatch(event)

    @filter.command("炼制", "炼制丹药")
    async def craft_danfang(self, event: AstrMessageEvent):
        """炼制丹药"""
        await self._dispatch(event)

    @filter.command("制作", "制作符箓")
    async def craft_zhizuo(self, event: AstrMessageEvent):
        """制作符箓"""
        await self._dispatch(event)

    @filter.command("打造", "打造装备")
    async def craft_equipment(self, event: AstrMessageEvent):
        """打造装备"""
        await self._dispatch(event)

    @filter.regex(r"^以(.+)修炼元神$")
    async def cultivate_yuanshen_with_gongfa(self, event: AstrMessageEvent):
        """以指定功法修炼元神"""
        await self._dispatch(event)

    @filter.command("我的灵根", "查看当前灵根")
    async def show_linggen(self, event: AstrMessageEvent):
        """查看当前灵根"""
        await self._dispatch(event)

    @filter.command("奏响往世乐土之章", "开启往世乐土仪式")
    async def start_elysia_ritual(self, event: AstrMessageEvent):
        """开启往世乐土仪式"""
        await self._dispatch(event)

    @filter.command("真我觉醒", "真我觉醒")
    async def awaken_zhenwo(self, event: AstrMessageEvent):
        """真我觉醒"""
        await self._dispatch(event)

    @filter.command("流萤觉醒", "流萤觉醒")
    async def awaken_liuying(self, event: AstrMessageEvent):
        """流萤觉醒"""
        await self._dispatch(event)

    @filter.command("圣体觉醒", "圣体觉醒")
    async def awaken_shengti(self, event: AstrMessageEvent):
        """圣体觉醒"""
        await self._dispatch(event)

    @filter.command("霸体觉醒", "霸体觉醒")
    async def awaken_bati(self, event: AstrMessageEvent):
        """霸体觉醒"""
        await self._dispatch(event)

    @filter.command("妖体觉醒", "妖体觉醒")
    async def awaken_yaoti(self, event: AstrMessageEvent):
        """妖体觉醒"""
        await self._dispatch(event)

    @filter.command("宗门列表", "查看宗门列表")
    async def list_sects(self, event: AstrMessageEvent):
        """查看宗门列表"""
        await self._dispatch(event)

    @filter.command("我的宗门", "查看我的宗门")
    async def show_my_sect(self, event: AstrMessageEvent):
        """查看我的宗门"""
        await self._dispatch(event)

    @filter.command("加入宗门", "加入指定宗门")
    async def join_sect(self, event: AstrMessageEvent):
        """加入指定宗门"""
        await self._dispatch(event)

    @filter.command("退出宗门", "退出当前宗门")
    async def leave_sect(self, event: AstrMessageEvent):
        """退出当前宗门"""
        await self._dispatch(event)

    @filter.command("宗门捐赠", "向宗门捐赠灵石")
    async def donate_sect(self, event: AstrMessageEvent):
        """向宗门捐赠灵石"""
        await self._dispatch(event)

    @filter.command("宗门俸禄", "领取宗门俸禄")
    async def sect_salary(self, event: AstrMessageEvent):
        """领取宗门俸禄"""
        await self._dispatch(event)

    @filter.command("宗门捐献榜", "查看宗门捐献榜")
    async def show_sect_donation_logs(self, event: AstrMessageEvent):
        """查看宗门捐献榜"""
        await self._dispatch(event)

    @filter.command("接取每日任务", "接取每日任务")
    async def accept_daily_task(self, event: AstrMessageEvent):
        """接取每日任务"""
        await self._dispatch(event)

    @filter.command("每日任务", "接取每日任务")
    async def daily_task(self, event: AstrMessageEvent):
        """接取每日任务"""
        await self._dispatch(event)

    @filter.command("提交每日任务", "提交每日任务")
    async def submit_daily_task(self, event: AstrMessageEvent):
        """提交每日任务"""
        await self._dispatch(event)

    @filter.command("领取每日任务奖励", "领取每日任务奖励")
    async def claim_daily_task_reward(self, event: AstrMessageEvent):
        """领取每日任务奖励"""
        await self._dispatch(event)

    @filter.command("供奉魔石", "供奉魔石升级魔根")
    async def upgrade_demon_root(self, event: AstrMessageEvent):
        """供奉魔石升级魔根"""
        await self._dispatch(event)

    @filter.command("堕入魔界", "堕入魔界修炼")
    async def enter_demon_realm(self, event: AstrMessageEvent):
        """堕入魔界修炼"""
        await self._dispatch(event)

    @filter.command("修炼魔功", "修炼魔功")
    async def cultivate_demon_art(self, event: AstrMessageEvent):
        """修炼魔功"""
        await self._dispatch(event)

    @filter.command("献祭魔石", "献祭魔石换取材料")
    async def sacrifice_spirit_stones(self, event: AstrMessageEvent):
        """献祭魔石换取材料"""
        await self._dispatch(event)

    @filter.command("放弃魔根", "放弃魔根")
    async def abandon_demon_root(self, event: AstrMessageEvent):
        """放弃魔根"""
        await self._dispatch(event)

    @filter.command("转世魔根", "转世魔根")
    async def convert_demon_root(self, event: AstrMessageEvent):
        """转世魔根"""
        await self._dispatch(event)

    @filter.command("探查", "探查商店状态")
    async def inspect_looting(self, event: AstrMessageEvent):
        """探查商店状态"""
        await self._dispatch(event)

    @filter.command("洗劫", "开始洗劫")
    async def start_looting(self, event: AstrMessageEvent):
        """开始洗劫"""
        await self._dispatch(event)

    @filter.command("洗劫归来", "结算洗劫")
    async def settle_looting(self, event: AstrMessageEvent):
        """结算洗劫"""
        await self._dispatch(event)

    @filter.command("重置洗劫", "重置商店状态")
    async def reset_looting(self, event: AstrMessageEvent):
        """重置商店状态"""
        await self._dispatch(event)

    @filter.command("开启收徒", "开启收徒")
    async def open_recruitment(self, event: AstrMessageEvent):
        """开启收徒"""
        await self._dispatch(event)

    @filter.command("关闭收徒", "关闭收徒")
    async def close_recruitment(self, event: AstrMessageEvent):
        """关闭收徒"""
        await self._dispatch(event)

    @filter.command("拜师", "拜师")
    async def apprentice(self, event: AstrMessageEvent):
        """拜师"""
        await self._dispatch(event)

    @filter.command("解除关系", "解除师徒关系")
    async def dissolve_shitu(self, event: AstrMessageEvent):
        """解除师徒关系"""
        await self._dispatch(event)

    @filter.command("师徒列表", "查看收徒列表")
    async def show_master_list(self, event: AstrMessageEvent):
        """查看收徒列表"""
        await self._dispatch(event)

    @filter.command("我的徒弟", "查看我的徒弟")
    async def show_my_apprentice(self, event: AstrMessageEvent):
        """查看我的徒弟"""
        await self._dispatch(event)

    @filter.command("我的师傅", "查看我的师傅")
    async def show_my_master(self, event: AstrMessageEvent):
        """查看我的师傅"""
        await self._dispatch(event)

    @filter.command("提交师徒任务", "提交师徒任务")
    async def submit_shitu_task(self, event: AstrMessageEvent):
        """提交师徒任务"""
        await self._dispatch(event)

    @filter.command("师徒试炼", "挑战师徒试炼")
    async def trial_shitu(self, event: AstrMessageEvent):
        """挑战师徒试炼"""
        await self._dispatch(event)

    @filter.command("师徒商店", "查看师徒商店")
    async def show_shitu_shop(self, event: AstrMessageEvent):
        """查看师徒商店"""
        await self._dispatch(event)

    @filter.command("兑换", "兑换师徒商店物品")
    async def exchange_shitu(self, event: AstrMessageEvent):
        """兑换师徒商店物品"""
        await self._dispatch(event)

    @filter.command("轮回", "九世轮回")
    async def reincarnate(self, event: AstrMessageEvent):
        """九世轮回"""
        await self._dispatch(event)

    @filter.command("确认轮回", "确认轮回")
    async def confirm_reincarnation(self, event: AstrMessageEvent):
        """确认轮回"""
        await self._dispatch(event)

    @filter.command("先不轮回", "取消轮回")
    async def cancel_reincarnation(self, event: AstrMessageEvent):
        """取消轮回"""
        await self._dispatch(event)

    @filter.command("验证自身成就", "验证并领取成就")
    async def check_chengjiu(self, event: AstrMessageEvent):
        """验证并领取成就"""
        await self._dispatch(event)

    @filter.command("修仙助手", "修仙助手")
    async def xiuxian_assistant(self, event: AstrMessageEvent):
        """修仙助手"""
        await self._dispatch(event)

    async def _dispatch(self, event: AstrMessageEvent) -> None:
        adapter = AstrBotAdapter(event)
        message = event.message_str
        # command_handler 内部仍按 # 前缀解析，触发时补回前缀
        if not message.startswith("#"):
            message = "#" + message
        handled = await self.command_handler.handle(adapter, message)
        if not handled:
            event.set_result(event.plain_result("未识别的指令。"))

    async def terminate(self):
        """插件卸载/停用时调用。"""
        pass
