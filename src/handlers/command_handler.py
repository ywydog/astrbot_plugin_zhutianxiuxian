from src.data.boss_data import BossData
from src.data.chengjiu_data import ChengjiuData
from src.data.exploration_data import ExplorationData
from src.data.item_data import ItemCatalog
from src.data.level_data import LevelData
from src.data.occupation_data import OccupationData
from src.data.sect_data import SectData
from src.data.shitu_data import ShituData, ShituShopData
from src.data.shop_data import ShopData
from src.data.tianjiao_data import TianjiaoData
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
from src.services.looting_service import LootingService
from src.services.pata_service import PataService
from src.services.team_boss_service import TeamBossService
from src.services.xiangu_jinshi_service import XianguJinshiService
from src.services.zhutianjing_service import ZhutianjingService
from src.services.occupation_service import OccupationService
from src.services.player_service import PlayerService
from src.services.ranking_service import RankingService
from src.services.reincarnation_service import ReincarnationService
from src.services.sect_service import SectService
from src.services.shitu_service import ShituService
from src.services.smallworld_service import SmallworldService
from src.services.tiandibang_service import TiandibangService
from src.services.tianjiao_service import TianjiaoService
from src.services.yuanshen_service import YuanshenService


class XiuxianCommandHandler:
    """修仙插件指令分发器，与具体 Bot 平台解耦。"""

    CATALOG_COMMANDS: dict[str, tuple[str, str]] = {
        "#装备楼": ("装备列表.json", "【装备楼】"),
        "#丹药楼": ("丹药列表.json", "【丹药楼】"),
        "#道具楼": ("道具列表.json", "【道具楼】"),
        "#功法楼": ("功法列表.json", "【功法楼】"),
        "#草药楼": ("草药列表.json", "【草药楼】"),
        "#食材楼": ("食材列表.json", "【食材楼】"),
        "#盒子楼": ("盒子列表.json", "【盒子楼】"),
        "#材料楼": ("材料列表.json", "【材料楼】"),
        "#仙宠楼": ("仙宠列表.json", "【仙宠楼】"),
        "#口粮楼": ("仙宠口粮列表.json", "【口粮楼】"),
        "#宝石楼": ("宝石.json", "【宝石楼】"),
    }

    def __init__(
        self,
        player_service: PlayerService,
        checkin_service: CheckinService | None = None,
        level_data: LevelData | None = None,
        breakthrough_service: BreakthroughService | None = None,
        cultivation_service: CultivationService | None = None,
        occupation_data: OccupationData | None = None,
        item_catalog: ItemCatalog | None = None,
        tianjiao_service: TianjiaoService | None = None,
        exploration_service: ExplorationService | None = None,
        exploration_data: ExplorationData | None = None,
        battle_service: BattleService | None = None,
        boss_service: BossService | None = None,
        boss_data: BossData | None = None,
        ranking_service: RankingService | None = None,
        lifespan_service: LifespanService | None = None,
        yuanshen_service: YuanshenService | None = None,
        inventory_service: InventoryService | None = None,
        gongfa_service: GongfaService | None = None,
        inner_world_service: InnerWorldService | None = None,
        occupation_service: OccupationService | None = None,
        linggen_service: LinggenService | None = None,
        sect_service: SectService | None = None,
        daily_task_service: DailyTaskService | None = None,
        demon_service: DemonService | None = None,
        looting_service: LootingService | None = None,
        reincarnation_service: ReincarnationService | None = None,
        shitu_service: ShituService | None = None,
        smallworld_service: SmallworldService | None = None,
        tiandibang_service: TiandibangService | None = None,
        sect_data: SectData | None = None,
        shop_data: ShopData | None = None,
        shitu_data: ShituData | None = None,
        shitu_shop_data: ShituShopData | None = None,
        chengjiu_service: ChengjiuService | None = None,
        xiangu_jinshi_service: XianguJinshiService | None = None,
        auction_service: AuctionService | None = None,
        exchange_service: ExchangeService | None = None,
        daolv_service: DaolvService | None = None,
        team_boss_service: TeamBossService | None = None,
        pata_service: PataService | None = None,
        zhutianjing_service: ZhutianjingService | None = None,
        admin_service: AdminService | None = None,
        master_ids: set[str] | None = None,
    ):
        self.player_service = player_service
        self.checkin_service = checkin_service
        self.level_data = level_data
        self.breakthrough_service = breakthrough_service
        self.cultivation_service = cultivation_service
        self.occupation_data = occupation_data
        self.item_catalog = item_catalog
        self.tianjiao_service = tianjiao_service
        self.exploration_service = exploration_service
        self.exploration_data = exploration_data
        self.battle_service = battle_service
        self.boss_service = boss_service
        self.boss_data = boss_data
        self.ranking_service = ranking_service
        self.lifespan_service = lifespan_service
        self.yuanshen_service = yuanshen_service
        self.inventory_service = inventory_service
        self.gongfa_service = gongfa_service
        self.inner_world_service = inner_world_service
        self.occupation_service = occupation_service
        self.linggen_service = linggen_service
        self.sect_service = sect_service
        self.daily_task_service = daily_task_service
        self.demon_service = demon_service
        self.looting_service = looting_service
        self.reincarnation_service = reincarnation_service
        self.shitu_service = shitu_service
        self.smallworld_service = smallworld_service
        self.tiandibang_service = tiandibang_service
        self.sect_data = sect_data
        self.shop_data = shop_data
        self.shitu_data = shitu_data
        self.shitu_shop_data = shitu_shop_data
        self.chengjiu_service = chengjiu_service
        self.xiangu_jinshi_service = xiangu_jinshi_service
        self.auction_service = auction_service
        self.exchange_service = exchange_service
        self.daolv_service = daolv_service
        self.team_boss_service = team_boss_service
        self.pata_service = pata_service
        self.zhutianjing_service = zhutianjing_service
        self.admin_service = admin_service
        self.master_ids = master_ids or set()

    async def handle(self, adapter, message: str) -> bool:
        """
        处理单条消息。
        :param adapter: 平台适配器，需实现 get_user_id / get_group_id / reply_text
        :param message: 原始消息文本
        :return: 是否命中指令
        """
        text = message.strip()

        if text == "#修仙帮助":
            await self._show_help(adapter)
            return True

        if text == "#刷新信息":
            await self._refresh_info(adapter)
            return True

        if text == "#踏入仙途":
            await self._start_cultivation(adapter)
            return True

        if text == "#我的练气":
            await self._show_player(adapter)
            return True

        if text == "#我的炼体":
            await self._show_physique(adapter)
            return True

        if text == "#我" or text == "#我的":
            await self._show_full_info(adapter)
            return True

        if text == "#突破":
            await self._breakthrough(adapter)
            return True

        if text == "#幸运突破":
            await self._lucky_breakthrough(adapter)
            return True

        if text == "#破体":
            await self._physique_breakthrough(adapter)
            return True

        if text == "#幸运破体":
            await self._lucky_physique_breakthrough(adapter)
            return True

        if text == "#修仙签到":
            await self._checkin(adapter)
            return True

        if text == "#修仙状态" or text == "#状态":
            await self._show_status(adapter)
            return True

        if text == "#练气境界":
            await self._show_cultivation_levels(adapter)
            return True

        if text == "#炼体境界":
            await self._show_physique_levels(adapter)
            return True

        if text == "#秘境体系":
            await self._show_mijing_levels(adapter)
            return True

        if text == "#仙古今世法":
            await self._show_xiangu_levels(adapter)
            return True

        if text == "#职业等级":
            await self._show_occupation_levels(adapter)
            return True

        if text in self.CATALOG_COMMANDS:
            await self._show_item_catalog(adapter, text)
            return True

        if text == "#一键突破":
            await self._auto_breakthrough(adapter)
            return True

        if text == "#一键破体":
            await self._auto_physique_breakthrough(adapter)
            return True

        if text.startswith("#设置性别"):
            await self._set_sex(adapter, text)
            return True

        if text.startswith("#改名"):
            await self._rename(adapter, text)
            return True

        if text.startswith("#设置道宣"):
            await self._set_motto(adapter, text)
            return True

        if text == "#闭关" or text.startswith("#闭关"):
            await self._start_seclusion(adapter, text)
            return True

        if text == "#出关":
            await self._end_seclusion(adapter)
            return True

        if text == "#降妖归来":
            await self._end_hunt(adapter)
            return True

        if text == "#降妖" or text.startswith("#降妖"):
            await self._start_hunt(adapter, text)
            return True

        if text == "#天骄列表":
            await self._show_tianjiao_list(adapter)
            return True

        if text == "#天骄状态" or text.startswith("#天骄状态"):
            await self._show_tianjiao_status(adapter, text)
            return True

        if text.startswith("#讨伐天骄"):
            await self._challenge_tianjiao(adapter, text)
            return True

        if text.startswith("#天骄贡献榜"):
            await self._show_tianjiao_damage_list(adapter, text)
            return True

        if text == "#开启天骄":
            await self._init_tianjiao(adapter)
            return True

        if text == "#关闭天骄":
            await self._close_tianjiao(adapter)
            return True

        if text == "#秘境":
            await self._show_secret_places(adapter)
            return True

        if text.startswith("#降临秘境"):
            await self._start_secret_place(adapter, text)
            return True

        if text == "#禁地":
            await self._show_forbidden_areas(adapter)
            return True

        if text.startswith("#前往禁地"):
            await self._start_forbidden_area(adapter, text)
            return True

        if text == "#仙府":
            await self._show_time_places(adapter)
            return True

        if text == "#探索仙府":
            await self._start_time_place(adapter)
            return True

        if text == "#仙境":
            await self._show_fairy_realms(adapter)
            return True

        if text.startswith("#镇守仙境"):
            await self._start_fairy_realm(adapter, text)
            return True

        if text == "#逃离":
            await self._give_up(adapter)
            return True

        if text.startswith("#副本掉落"):
            await self._show_dungeon_drop(adapter, text)
            return True

        if text == "#打劫":
            await self._rob(adapter)
            return True

        if text == "#比武":
            await self._duel(adapter)
            return True

        if text == "#开启妖王":
            await self._init_boss(adapter)
            return True

        if text == "#关闭妖王":
            await self._close_boss(adapter)
            return True

        if text == "#妖王状态":
            await self._show_boss_status(adapter)
            return True

        if text == "#妖王贡献榜":
            await self._show_boss_damage_list(adapter)
            return True

        if text == "#讨伐妖王":
            await self._challenge_boss(adapter)
            return True

        if text == "#魔道榜":
            await self._show_modao_ranking(adapter)
            return True

        if text == "#强化榜":
            await self._show_enhance_ranking(adapter)
            return True

        if text == "#天榜":
            await self._show_exp_ranking(adapter)
            return True

        if text == "#灵榜":
            await self._show_spirit_stones_ranking(adapter)
            return True

        if text == "#封神榜":
            await self._show_fengshen_ranking(adapter)
            return True

        if text == "#遮天榜":
            await self._show_zhetian_ranking(adapter)
            return True

        if text == "#完美世界榜":
            await self._show_xiangu_ranking(adapter)
            return True

        if text == "#至尊榜":
            await self._show_zhizun_ranking(adapter)
            return True

        if text == "#镇妖塔榜":
            await self._show_zhenyao_ranking(adapter)
            return True

        if text == "#神魄榜":
            await self._show_shenpo_ranking(adapter)
            return True

        # ---------- 天地榜 ----------
        if text == "#报名比赛":
            await self._tiandibang_register(adapter)
            return True

        if text == "#更新属性":
            await self._tiandibang_update(adapter)
            return True

        if text == "#天地榜":
            await self._tiandibang_ranking(adapter)
            return True

        if text == "#比试":
            await self._tiandibang_challenge(adapter)
            return True

        if text == "#天地堂":
            await self._tiandibang_shop(adapter)
            return True

        if text.startswith("#积分兑换"):
            await self._tiandibang_exchange(adapter, text)
            return True

        if text == "#结算天地榜奖励":
            await self._tiandibang_settle(adapter)
            return True

        if text == "#清空积分":
            await self._tiandibang_reset(adapter)
            return True

        # ---------- 小世界 ----------
        if text.startswith("#开辟小世界"):
            await self._smallworld_create(adapter, text)
            return True

        if text == "#演化小世界":
            await self._smallworld_upgrade(adapter)
            return True

        if text == "#我的小世界":
            await self._smallworld_view(adapter)
            return True

        if text == "#将分身化入小世界":
            await self._smallworld_avatar(adapter)
            return True

        if text == "#收获小世界资源":
            await self._smallworld_harvest(adapter)
            return True

        if text == "#种植指南":
            await self._smallworld_planting_help(adapter)
            return True

        if text.startswith("#小世界栽种"):
            await self._smallworld_plant(adapter, text)
            return True

        if text.startswith("#使用") and "浇灌" in text:
            await self._smallworld_water_single(adapter, text)
            return True

        if text == "#浇灌小世界作物":
            await self._smallworld_water_all(adapter)
            return True

        if text.startswith("#使用") and text.endswith("创造环境"):
            await self._smallworld_create_environment(adapter, text)
            return True

        if text == "#催熟小世界作物":
            await self._smallworld_force_ripen(adapter)
            return True

        if text == "#查看寿元":
            await self._show_lifespan(adapter)
            return True

        if text == "#执行寿元流逝":
            await self._reduce_lifespan_manual(adapter, 1000)
            return True

        if text.startswith("#执行寿元流逝"):
            await self._reduce_lifespan_manual(adapter, text)
            return True

        if text == "#我的元神":
            await self._show_yuanshen(adapter)
            return True

        if text == "#凝练元神":
            await self._condense_yuanshen(adapter)
            return True

        if text == "#开启内景地":
            await self._open_neijing(adapter)
            return True

        if text == "#进入内景地":
            await self._enter_neijing(adapter)
            return True

        if text == "#内景地修炼" or text.startswith("#内景地修炼"):
            await self._neijing_batch(adapter, text)
            return True

        if text == "#开辟内景地空间":
            await self._open_inner_world(adapter)
            return True

        if text == "#查看内景地" or text == "#我的内景地":
            await self._view_inner_world(adapter)
            return True

        if text == "#升级内景地空间" or text == "#升级内景地":
            await self._upgrade_inner_world(adapter)
            return True

        if text.startswith("#存入"):
            await self._store_inner_world(adapter, text)
            return True

        if text.startswith("#取出"):
            await self._take_inner_world(adapter, text)
            return True

        if text == "#一键存入内景地" or text == "#一键存入":
            await self._store_all_inner_world(adapter)
            return True

        if text == "#一键取出内景地" or text == "#一键取出":
            await self._take_all_inner_world(adapter)
            return True

        if text.startswith("#按类别取出") or text.startswith("#取出类别"):
            await self._take_category_inner_world(adapter, text)
            return True

        if text == "#冲关":
            await self._xiangu_breakthrough(adapter, False)
            return True

        if text == "#冲关极境":
            await self._xiangu_breakthrough(adapter, True)
            return True

        if text.startswith("#拍卖"):
            await self._create_auction(adapter, text)
            return True

        if text == "#查看当前拍卖":
            await self._show_auction(adapter)
            return True

        if text.startswith("#竞价"):
            await self._bid_auction(adapter, text)
            return True

        if text.startswith("#交易"):
            await self._create_exchange_sell(adapter, text)
            return True

        if text == "#查看交易":
            await self._show_exchange(adapter)
            return True

        if text.startswith("#购买"):
            await self._buy_exchange(adapter, text)
            return True

        if text.startswith("#求购"):
            await self._create_exchange_buy(adapter, text)
            return True

        if text.startswith("#下架"):
            await self._remove_exchange(adapter, text)
            return True

        if text.startswith("#结为道侣"):
            await self._propose_daolv(adapter, text)
            return True

        if text == "#同意道侣":
            await self._respond_daolv(adapter, accept=True)
            return True

        if text == "#拒绝道侣":
            await self._respond_daolv(adapter, accept=False)
            return True

        if text == "#我的道侣":
            await self._show_daolv(adapter)
            return True

        if text.startswith("#赠送百合花篮"):
            await self._gift_daolv(adapter, text)
            return True

        if text.startswith("#断绝姻缘"):
            await self._breakup_daolv(adapter, text)
            return True

        if text.startswith("#开启团本"):
            await self._create_team_boss(adapter, text)
            return True

        if text == "#加入团本":
            await self._join_team_boss(adapter)
            return True

        if text == "#退出团本":
            await self._leave_team_boss(adapter)
            return True

        if text == "#攻击团本":
            await self._attack_team_boss(adapter)
            return True

        if text == "#团本状态":
            await self._status_team_boss(adapter)
            return True

        if text == "#结算团本":
            await self._settle_team_boss(adapter)
            return True

        if text == "#挑战镇妖塔":
            await self._challenge_zhenyao(adapter)
            return True

        if text == "#一键镇妖塔":
            await self._auto_challenge_zhenyao(adapter)
            return True

        if text == "#我的镇妖塔":
            await self._show_zhenyao(adapter)
            return True

        if text == "#挑战锻神池":
            await self._challenge_shenpo(adapter)
            return True

        if text == "#一键锻神池":
            await self._auto_challenge_shenpo(adapter)
            return True

        if text == "#我的锻神池":
            await self._show_shenpo(adapter)
            return True

        if text == "#穿越诸天镜":
            await self._enter_zhutianjing(adapter)
            return True

        if text.startswith("#救赎"):
            await self._redeem_zhutianjing(adapter, text)
            return True

        if text == "#魔法少女进阶":
            await self._advance_magic_girl(adapter)
            return True

        if text == "#我的诸天镜":
            await self._show_zhutianjing(adapter)
            return True

        if text == "#库洛牌":
            await self._draw_clow_card(adapter)
            return True

        if text == "#备份存档":
            await self._backup_data(adapter)
            return True

        if text.startswith("#恢复备份"):
            await self._restore_backup(adapter, text)
            return True

        if text.startswith("#管理员加灵石"):
            await self._admin_add_spirit_stones(adapter, text)
            return True

        if text.startswith("#管理员加源石"):
            await self._admin_add_source_stones(adapter, text)
            return True

        if text.startswith("#管理员封号"):
            await self._admin_ban(adapter, text)
            return True

        if text.startswith("#管理员解封"):
            await self._admin_unban(adapter, text)
            return True

        if text.startswith("#设置时代"):
            await self._admin_set_era(adapter, text)
            return True

        if text == "#下一个时代":
            await self._admin_next_era(adapter)
            return True

        if text == "#纪元":
            await self._admin_show_era(adapter)
            return True

        if text.startswith("#自动任务"):
            await self._admin_auto_task(adapter, text)
            return True

        if text == "#我的纳戒" or text == "#纳戒":
            await self._show_inventory(adapter)
            return True

        if text == "#我的功法":
            await self._show_gongfa(adapter)
            return True

        if text.startswith("#学习功法"):
            await self._learn_gongfa(adapter, text)
            return True

        if text == "#我的职业":
            await self._show_occupation(adapter)
            return True

        if text.startswith("#转职"):
            await self._change_occupation(adapter, text)
            return True

        if text == "#转换副职":
            await self._swap_secondary_occupation(adapter)
            return True

        if text.startswith("#猎户转"):
            await self._change_from_liehu(adapter, text)
            return True

        if text == "#采药" or text.startswith("#采药"):
            await self._start_occupation_action(adapter, text, "采药")
            return True

        if text == "#结束采药":
            await self._end_occupation_action(adapter, "采药")
            return True

        if text == "#采矿" or text.startswith("#采矿"):
            await self._start_occupation_action(adapter, text, "采矿")
            return True

        if text == "#结束采矿":
            await self._end_occupation_action(adapter, "采矿")
            return True

        if text == "#狩猎" or text.startswith("#狩猎"):
            await self._start_occupation_action(adapter, text, "狩猎")
            return True

        if text == "#结束狩猎":
            await self._end_occupation_action(adapter, "狩猎")
            return True

        if text == "#寻源" or text.startswith("#寻源"):
            await self._start_occupation_action(adapter, text, "寻源")
            return True

        if text == "#结束寻源":
            await self._end_occupation_action(adapter, "寻源")
            return True

        if text == "#寻脉定源" or text.startswith("#寻脉定源"):
            await self._start_occupation_action(adapter, text, "寻脉定源")
            return True

        if text == "#结束寻脉定源":
            await self._end_occupation_action(adapter, "寻脉定源")
            return True

        if text == "#地脉引气" or text.startswith("#地脉引气"):
            await self._start_occupation_action(adapter, text, "地脉引气")
            return True

        if text == "#结束地脉引气":
            await self._end_occupation_action(adapter, "地脉引气")
            return True

        if text == "#丹药配方":
            await self._show_recipes(adapter, "danfang", "【丹药配方】")
            return True

        if text == "#符道配方":
            await self._show_recipes(adapter, "zhizuo", "【符道配方】")
            return True

        if text == "#装备图纸":
            await self._show_recipes(adapter, "tuzhi", "【装备图纸】")
            return True

        if text.startswith("#炼制"):
            await self._craft_danfang(adapter, text)
            return True

        if text.startswith("#制作"):
            await self._craft_zhizuo(adapter, text)
            return True

        if text.startswith("#打造"):
            await self._craft_equipment(adapter, text)
            return True

        if text.startswith("以") and text.endswith("修炼元神"):
            await self._cultivate_yuanshen_with_gongfa(adapter, text)
            return True

        if text == "#我的灵根":
            await self._show_linggen(adapter)
            return True

        if text == "#奏响往世乐土之章":
            await self._start_elysia_ritual(adapter)
            return True

        if text == "#真我觉醒":
            await self._awaken_zhenwo(adapter)
            return True

        if text == "#流萤觉醒":
            await self._awaken_liuying(adapter)
            return True

        if text == "#圣体觉醒":
            await self._awaken_shengti(adapter)
            return True

        if text == "#霸体觉醒":
            await self._awaken_bati(adapter)
            return True

        if text == "#妖体觉醒":
            await self._awaken_yaoti(adapter)
            return True

        # ---------- 宗门 ----------
        if text == "#宗门列表":
            await self._list_sects(adapter)
            return True

        if text == "#我的宗门":
            await self._show_my_sect(adapter)
            return True

        if text.startswith("#加入宗门"):
            await self._join_sect(adapter, text)
            return True

        if text == "#退出宗门":
            await self._leave_sect(adapter)
            return True

        if text.startswith("#宗门捐赠"):
            await self._donate_sect(adapter, text)
            return True

        if text == "#宗门俸禄":
            await self._sect_salary(adapter)
            return True

        if text == "#宗门捐献榜":
            await self._show_sect_donation_logs(adapter)
            return True

        # ---------- 每日任务 ----------
        if text == "#接取每日任务" or text == "#每日任务":
            await self._accept_daily_task(adapter)
            return True

        if text == "#提交每日任务":
            await self._submit_daily_task(adapter)
            return True

        if text == "#领取每日任务奖励":
            await self._claim_daily_task_reward(adapter)
            return True

        # ---------- 魔头 ----------
        if text == "#供奉魔石":
            await self._upgrade_demon_root(adapter)
            return True

        if text == "#堕入魔界":
            await self._enter_demon_realm(adapter)
            return True

        if text == "#修炼魔功":
            await self._cultivate_demon_art(adapter)
            return True

        if text.startswith("#献祭魔石"):
            await self._sacrifice_spirit_stones(adapter, text)
            return True

        if text == "#放弃魔根" or text == "#转世魔根":
            await self._handle_demon_choice(adapter, text)
            return True

        # ---------- 洗劫 ----------
        if text.startswith("#探查"):
            await self._inspect_looting(adapter, text)
            return True

        if text.startswith("#洗劫") and not text.startswith("#洗劫归来"):
            await self._start_looting(adapter, text)
            return True

        if text == "#洗劫归来":
            await self._settle_looting(adapter)
            return True

        if text.startswith("#重置洗劫"):
            await self._reset_looting(adapter, text)
            return True

        # ---------- 师徒 ----------
        if text == "#开启收徒":
            await self._open_recruitment(adapter)
            return True

        if text == "#关闭收徒":
            await self._close_recruitment(adapter)
            return True

        if text == "#拜师":
            await self._apprentice(adapter)
            return True

        if text == "#解除关系":
            await self._dissolve_shitu(adapter)
            return True

        if text == "#师徒列表":
            await self._show_master_list(adapter)
            return True

        if text == "#我的徒弟":
            await self._show_my_apprentice(adapter)
            return True

        if text == "#我的师傅":
            await self._show_my_master(adapter)
            return True

        if text == "#提交师徒任务":
            await self._submit_shitu_task(adapter)
            return True

        if text == "#师徒试炼":
            await self._trial_shitu(adapter)
            return True

        if text == "#师徒商店":
            await self._show_shitu_shop(adapter)
            return True

        if text.startswith("#兑换"):
            await self._exchange_shitu(adapter, text)
            return True

        # ---------- 轮回 ----------
        if text == "#轮回":
            await self._reincarnate(adapter)
            return True

        if text == "#确认轮回" or text == "#先不轮回":
            await self._confirm_reincarnation(adapter, text)
            return True

        if text == "#验证自身成就":
            await self._check_chengjiu(adapter)
            return True

        if text == "#修仙助手":
            await self._xiuxian_assistant(adapter)
            return True

        return False

    async def _checkin(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.checkin_service is None:
            await adapter.reply_text("签到服务未初始化。")
            return

        result = await self.checkin_service.daily_checkin(user_id)

        if result.already_signed:
            await adapter.reply_text(
                f"道友今日已签到，当前连续签到 {result.consecutive_days} 天。"
            )
            return

        await adapter.reply_text(
            f"签到成功！连续签到 {result.consecutive_days} 天\n"
            f"获得灵石 {result.spirit_stones_gained}\n"
            f"获得源石 {result.source_stones_gained}\n"
            f"获得修为 {result.exp_gained}\n"
            f"获得血气 {result.blood_qi_gained}"
        )

    async def _start_cultivation(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if await self.player_service.exists(user_id):
            await adapter.reply_text("道友已踏上仙途，无需再次入门。")
            return

        player = await self.player_service.create_player(user_id)
        name = player.get("name", "无名")
        linggen = player.get("linggen", {})
        linggen_type = linggen.get("type", "未知")
        evaluation = player.get("talent_evaluation", "未知")

        await adapter.reply_text(
            f"欢迎 {name} 踏入仙途！\n"
            f"灵根：{linggen_type}\n"
            f"天资：{evaluation}\n"
            f"可发送 #我的练气 查看状态。"
        )

    async def _refresh_info(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        result = await self.player_service.refresh_player(user_id)
        if result is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        player, fixed = result
        if not fixed:
            await adapter.reply_text("信息无需刷新。")
            return

        await adapter.reply_text(
            f"信息刷新完成，共补全 {len(fixed)} 项字段。\n"
            f"当前境界：{self.level_data.get_cultivation_name(player.get('level_id', 1))}\n"
            f"炼体境界：{self.level_data.get_physique_name(player.get('physique_id', 1))}\n"
            f"可发送 #我的 查看完整信息。"
        )

    async def _show_help(self, adapter) -> None:
        help_text = (
            "【修仙指令列表】\n"
            "基础：#踏入仙途 #我的练气 #我的炼体 #我的 #修仙状态\n"
            "养成：#修仙签到 #闭关 #出关 #降妖 #降妖归来\n"
            "境界：#练气境界 #炼体境界 #秘境体系 #仙古今世法\n"
            "突破：#突破 #破体 #幸运突破 #幸运破体 #一键突破 #一键破体\n"
            "信息楼：#装备楼 #丹药楼 #道具楼 #功法楼 #草药楼 #食材楼 #盒子楼 #材料楼 #仙宠楼 #口粮楼 #宝石楼\n"
            "天骄：#天骄列表 #天骄状态 #讨伐天骄 #天骄贡献榜\n"
            "探索：#秘境 #降临秘境 #禁地 #前往禁地 #仙府 #探索仙府 #仙境 #镇守仙境 #逃离 #副本掉落\n"
            "战斗：#打劫 @道友 #比武 @道友\n"
            "妖王：#开启妖王 #关闭妖王 #妖王状态 #妖王贡献榜 #讨伐妖王\n"
            "排行：#魔道榜 #强化榜 #天榜 #灵榜 #封神榜 #遮天榜 #完美世界榜 #至尊榜 #镇妖塔榜 #神魄榜\n"
            "天地榜：#报名比赛 #更新属性 #天地榜 #比试 #天地堂 #积分兑换 物品名*数量\n"
            "天地榜管理：#结算天地榜奖励 #清空积分\n"
            "寿元：#查看寿元\n"
            "元神：#我的元神 #凝练元神 #开启内景地 #进入内景地 #内景地修炼*N\n"
            "内景地空间：#开辟内景地空间 #查看内景地 #升级内景地空间\n"
            "           #存入 物品名*数量 #取出 物品名*数量\n"
            "           #一键存入内景地 #一键取出内景地 #按类别取出 类别\n"
            "纳戒：#我的纳戒 #纳戒\n"
            "功法：#我的功法 #学习功法 功法名 以功法名修炼元神\n"
            "职业：#我的职业 #转职 职业名 #转换副职 #猎户转 职业名\n"
            "职业动作：#采药 #结束采药 #采矿 #结束采矿 #狩猎 #结束狩猎\n"
            "        #寻源 #结束寻源 #寻脉定源 #结束寻脉定源 #地脉引气 #结束地脉引气\n"
            "职业配方：#丹药配方 #符道配方 #装备图纸\n"
            "职业炼制：#炼制 丹药名*数量 #制作 符名*数量 #打造 装备名\n"
            "灵根：#我的灵根 #奏响往世乐土之章 #真我觉醒 #流萤觉醒 #圣体觉醒 #霸体觉醒 #妖体觉醒\n"
            "宗门：#宗门列表 #我的宗门 #加入宗门 宗门名 #退出宗门 #宗门捐赠 数量 #宗门俸禄 #宗门捐献榜\n"
            "每日任务：#接取每日任务 #提交每日任务 #领取每日任务奖励\n"
            "魔头：#供奉魔石 #堕入魔界 #修炼魔功 #献祭魔石*次数\n"
            "洗劫：#探查 地点 #洗劫 地点 #洗劫归来 #重置洗劫 地点\n"
            "师徒：#开启收徒 #关闭收徒 #拜师 @师傅 #解除关系 #师徒列表 #我的徒弟 #我的师傅\n"
            "      #提交师徒任务 #师徒试炼 #师徒商店 #兑换 物品名\n"
            "轮回：#轮回 #确认轮回 #先不轮回\n"
            "小世界：#开辟小世界 名字 #演化小世界 #我的小世界\n"
            "        #将分身化入小世界 #收获小世界资源 #种植指南\n"
            "        #小世界栽种 种子名 #浇灌小世界作物\n"
            "        #使用[草木精华露/岁月流金沙/掌天灵液]浇灌[位置]\n"
            "        #使用[道具]创造环境\n"
            "成就：#验证自身成就 #修仙助手\n"
            "设置：#设置性别 #改名 #设置道宣 #刷新信息\n"
            "发送对应指令即可体验。"
        )
        await adapter.reply_text(help_text)

    async def _show_player(self, adapter) -> None:
        user_id = await adapter.get_user_id()
        player = await self.player_service.load(user_id)

        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(self._format_player_info(player))

    async def _show_physique(self, adapter) -> None:
        user_id = await adapter.get_user_id()
        player = await self.player_service.load(user_id)

        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(self._format_physique_info(player))

    async def _show_full_info(self, adapter) -> None:
        user_id = await adapter.get_user_id()
        player = await self.player_service.load(user_id)

        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(self._format_full_info(player))

    async def _show_status(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.cultivation_service is None:
            await adapter.reply_text("修炼服务未初始化。")
            return

        action = await self.cultivation_service.get_current_action(user_id)
        if action is None:
            await adapter.reply_text("【修仙状态】\n当前空闲，无事可做。")
            return

        await adapter.reply_text(
            f"【修仙状态】\n"
            f"当前动作：{action['action']}\n"
            f"剩余时间：{action['remaining_minutes']} 分 {action['remaining_seconds']} 秒"
        )

    async def _show_cultivation_levels(self, adapter) -> None:
        if self.level_data is None:
            await adapter.reply_text("境界数据未初始化。")
            return

        lines = ["【练气境界表】"]
        for item in self.level_data.cultivation_levels:
            lines.append(
                f"{item.get('level_id')}·{item.get('level')} "
                f"| 所需修为：{item.get('exp', 0)} "
                f"| 基础血量：{item.get('基础血量', 0)}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _show_physique_levels(self, adapter) -> None:
        if self.level_data is None:
            await adapter.reply_text("境界数据未初始化。")
            return

        lines = ["【炼体境界表】"]
        for item in self.level_data.physique_levels:
            lines.append(
                f"{item.get('level_id')}·{item.get('level')} "
                f"| 所需血气：{item.get('exp', 0)} "
                f"| 基础血量：{item.get('基础血量', 0)}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _show_mijing_levels(self, adapter) -> None:
        if self.level_data is None:
            await adapter.reply_text("境界数据未初始化。")
            return

        lines = ["【秘境体系】"]
        for item in self.level_data.mijing_levels:
            lines.append(
                f"{item.get('level_id')}·{item.get('level')} "
                f"| 攻：{item.get('基础攻击', 0)} "
                f"| 防：{item.get('基础防御', 0)} "
                f"| 血：{item.get('基础血量', 0)}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _show_xiangu_levels(self, adapter) -> None:
        if self.level_data is None:
            await adapter.reply_text("境界数据未初始化。")
            return

        lines = ["【仙古今世法】"]
        for item in self.level_data.xiangu_levels:
            extra = item.get("极境名称")
            extra_text = f" | 极境：{extra}" if extra else ""
            lines.append(
                f"{item.get('level_id')}·{item.get('level')} "
                f"| 攻：{item.get('基础攻击', 0)} "
                f"| 防：{item.get('基础防御', 0)} "
                f"| 血：{item.get('基础血量', 0)}"
                f"{extra_text}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _show_occupation_levels(self, adapter) -> None:
        if self.occupation_data is None:
            await adapter.reply_text("职业数据未初始化。")
            return

        lines = ["【职业列表】"]
        for item in self.occupation_data.occupations:
            lines.append(f"{item.get('id')}·{item.get('name')}")
        await adapter.reply_text("\n".join(lines))

    async def _show_occupation(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        result = await self.occupation_service.get_info(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        secondary_text = "无"
        if result.secondary:
            secondary_text = (
                f"{result.secondary.get('职业名', '')} "
                f"Lv.{result.secondary.get('职业等级', 1)}"
            )

        await adapter.reply_text(
            f"【我的职业】\n"
            f"当前职业：{result.occupation or '未就职'}\n"
            f"职业等级：{result.occupation_level}\n"
            f"职业经验：{result.occupation_exp}\n"
            f"副职：{secondary_text}"
        )

    async def _change_occupation(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        name = text[len("#转职"):].strip()
        if not name:
            await adapter.reply_text("格式：#转职 职业名")
            return

        result = await self.occupation_service.change_occupation(user_id, name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"转职失败：{result.reason}")
            return

        msg = f"恭喜转职为【{result.occupation}】"
        if result.secondary_name:
            msg += f"，副职记录为【{result.secondary_name}】"
        await adapter.reply_text(msg)

    async def _change_from_liehu(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        name = text[len("#猎户转"):].strip()
        if not name:
            await adapter.reply_text("格式：#猎户转 职业名")
            return

        result = await self.occupation_service.change_occupation_from_liehu(user_id, name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"转职失败：{result.reason}")
            return

        await adapter.reply_text(f"恭喜转职为【{result.occupation}】")

    async def _swap_secondary_occupation(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        result = await self.occupation_service.swap_secondary_occupation(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"转换副职失败：{result.reason}")
            return

        await adapter.reply_text(
            f"当前职业切换为【{result.occupation}】，"
            f"副职记录为【{result.secondary_name}】"
        )

    def _parse_action_minutes(self, text: str, prefix: str, default: int) -> int:
        remaining = text[len(prefix):].strip()
        remaining = remaining.replace("分钟", "").replace("分", "").replace(" ", "")
        if not remaining:
            return default
        try:
            return int(remaining)
        except ValueError:
            return default

    async def _start_occupation_action(self, adapter, text: str, action_name: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        minutes = self._parse_action_minutes(text, f"#{action_name}", 30)
        result = await self.occupation_service.start_action(user_id, action_name, minutes)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(f"现在开始{result.action}{result.minutes}分钟")

    async def _end_occupation_action(self, adapter, action_name: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        result = await self.occupation_service.end_action(user_id, action_name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        lines = [result.message]
        if result.items:
            lines.append("收获：")
            for item in result.items:
                lines.append(f"  {item['name']} x{item['quantity']}")
        await adapter.reply_text("\n".join(lines))

    async def _show_recipes(self, adapter, recipe_type: str, title: str) -> None:
        if self.occupation_service is None or self.occupation_data is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        recipes = self.occupation_data.recipes.get(recipe_type, [])
        if not recipes:
            await adapter.reply_text(f"{title}\n暂无数据。")
            return

        lines = [title]
        for recipe in recipes[:20]:
            name = recipe.get("name", "未知")
            level = recipe.get("level_limit", 0)
            lines.append(f"{name} | 需求等级：{level}")
        if len(recipes) > 20:
            lines.append(f"……共 {len(recipes)} 项，仅展示前 20 项")
        await adapter.reply_text("\n".join(lines))

    def _parse_craft_args(self, text: str, prefix: str) -> tuple[str, int]:
        remaining = text[len(prefix):].strip()
        if not remaining:
            return "", 1
        parts = remaining.split("*", 1)
        name = parts[0].strip()
        quantity = 1
        if len(parts) > 1:
            try:
                quantity = max(1, int(parts[1].strip()))
            except ValueError:
                quantity = 1
        return name, quantity

    async def _craft_danfang(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        name, quantity = self._parse_craft_args(text, "#炼制")
        if not name:
            await adapter.reply_text("格式：#炼制 丹药名*数量")
            return

        result = await self.occupation_service.craft_danfang(user_id, name, quantity)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        quality_text = f"（{result.quality}）" if result.quality else ""
        await adapter.reply_text(
            f"炼制成功！\n"
            f"获得 {result.name}{quality_text} x{result.quantity}\n"
            f"获得炼丹经验 {result.exp_gained}"
        )

    async def _craft_zhizuo(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        name, quantity = self._parse_craft_args(text, "#制作")
        if not name:
            await adapter.reply_text("格式：#制作 符名*数量")
            return

        result = await self.occupation_service.craft_zhizuo(user_id, name, quantity)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(
            f"制作成功！\n"
            f"获得 {result.name} x{result.quantity}\n"
            f"获得制符经验 {result.exp_gained}"
        )

    async def _craft_equipment(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.occupation_service is None:
            await adapter.reply_text("职业服务未初始化。")
            return

        name, _ = self._parse_craft_args(text, "#打造")
        if not name:
            await adapter.reply_text("格式：#打造 装备名")
            return

        result = await self.occupation_service.craft_equipment(user_id, name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        quality_text = f"（{result.quality}）" if result.quality else ""
        await adapter.reply_text(
            f"打造成功！\n"
            f"获得 {result.name}{quality_text} x{result.quantity}\n"
            f"获得炼器经验 {result.exp_gained}"
        )

    async def _show_item_catalog(self, adapter, command: str) -> None:
        if self.item_catalog is None:
            await adapter.reply_text("物品数据未初始化。")
            return

        filename, title = self.CATALOG_COMMANDS[command]
        items = self.item_catalog.get_items(filename)
        if not items:
            await adapter.reply_text(f"{title}\n暂无数据。")
            return

        lines = [title]
        for item in items[:20]:
            item_id = item.get("id")
            name = item.get("name", "未知")
            item_type = item.get("type", "")
            id_text = f"{item_id}·" if item_id is not None else ""
            type_text = f"（{item_type}）" if item_type else ""
            lines.append(f"{id_text}{name}{type_text}")
        if len(items) > 20:
            lines.append(f"……共 {len(items)} 项，仅展示前 20 项")
        await adapter.reply_text("\n".join(lines))

    async def _breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_cultivation_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.success:
            await adapter.reply_text(f"突破失败：{result.reason}")
            return

        await adapter.reply_text(
            f"突破成功！\n"
            f"境界提升至 {result.level_name}（{result.new_level} 层）"
        )

    async def _physique_breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_physique_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.success:
            await adapter.reply_text(f"破体失败：{result.reason}")
            return

        await adapter.reply_text(
            f"破体成功！\n"
            f"炼体境界提升至 {result.level_name}（{result.new_level} 层）"
        )

    async def _lucky_breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_cultivation_lucky_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.success:
            await adapter.reply_text(f"幸运突破失败：{result.reason}")
            return

        await adapter.reply_text(
            f"幸运突破成功！\n"
            f"境界提升至 {result.level_name}（{result.new_level} 层）\n"
            f"消耗 500 灵石"
        )

    async def _lucky_physique_breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_physique_lucky_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.success:
            await adapter.reply_text(f"幸运破体失败：{result.reason}")
            return

        await adapter.reply_text(
            f"幸运破体成功！\n"
            f"炼体境界提升至 {result.level_name}（{result.new_level} 层）\n"
            f"消耗 500 灵石"
        )

    async def _auto_breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_cultivation_auto_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.total_levels == 0:
            await adapter.reply_text(f"一键突破失败：{result.reason}")
            return

        await adapter.reply_text(
            f"一键突破完成！\n"
            f"共突破 {result.total_levels} 层\n"
            f"当前境界：{result.level_name}（{result.final_level} 层）\n"
            f"停止原因：{result.reason if result.reason else '已达最高境界或资源耗尽'}"
        )

    async def _auto_physique_breakthrough(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.breakthrough_service is None:
            await adapter.reply_text("突破服务未初始化。")
            return

        result = await self.breakthrough_service.attempt_physique_auto_breakthrough(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.total_levels == 0:
            await adapter.reply_text(f"一键破体失败：{result.reason}")
            return

        await adapter.reply_text(
            f"一键破体完成！\n"
            f"共突破 {result.total_levels} 层\n"
            f"当前炼体境界：{result.level_name}（{result.final_level} 层）\n"
            f"停止原因：{result.reason if result.reason else '已达最高境界或资源耗尽'}"
        )

    async def _set_sex(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        player = await self.player_service.load(user_id)
        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if player.get("sex", 0) != 0:
            await adapter.reply_text("每个存档仅可设置一次性别！")
            return

        msg = text[len("#设置性别"):].strip()
        if "男" in msg:
            player["sex"] = 2
        elif "女" in msg:
            player["sex"] = 1
        else:
            await adapter.reply_text("格式错误，请使用：#设置性别 男 / #设置性别 女")
            return

        await self.player_service.save(user_id, player)
        await adapter.reply_text(
            f"{player.get('name', '道友')}的性别已成功设置为 {'男' if player['sex'] == 2 else '女'}。"
        )

    async def _rename(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        player = await self.player_service.load(user_id)
        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        new_name = text[len("#改名"):].strip().replace(" ", "").replace("+", "")
        if not new_name:
            await adapter.reply_text("格式：#改名 新名字")
            return
        if len(new_name) > 8:
            await adapter.reply_text("玩家名字最多八字")
            return

        if player.get("spirit_stones", 0) < 1000:
            await adapter.reply_text("改名需要 1000 灵石")
            return

        player["name"] = new_name
        player["spirit_stones"] = player.get("spirit_stones", 0) - 1000
        await self.player_service.save(user_id, player)
        await adapter.reply_text(f"改名成功！道号已更改为 {new_name}，消耗 1000 灵石。")

    async def _set_motto(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        player = await self.player_service.load(user_id)
        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        new_motto = text[len("#设置道宣"):].strip().replace(" ", "").replace("+", "")
        if not new_motto:
            await adapter.reply_text("格式：#设置道宣 内容")
            return
        if len(new_motto) > 50:
            await adapter.reply_text("道宣最多 50 字符")
            return

        player["motto"] = new_motto
        await self.player_service.save(user_id, player)
        await adapter.reply_text(f"道宣已设置为：{new_motto}")

    def _parse_minutes(self, text: str, prefix: str, default: int) -> int:
        remaining = text[len(prefix):].strip()
        remaining = remaining.replace("分钟", "").replace("分", "").replace(" ", "")
        if not remaining:
            return default
        try:
            return int(remaining)
        except ValueError:
            return default

    async def _start_seclusion(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.cultivation_service is None:
            await adapter.reply_text("修炼服务未初始化。")
            return

        minutes = self._parse_minutes(text, "#闭关", 60)
        result = await self.cultivation_service.start_seclusion(user_id, minutes)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法闭关：{result.reason}")
            return

        await adapter.reply_text(f"开始闭关 {result.elapsed_minutes} 分钟，两耳不闻窗外事。")

    async def _end_seclusion(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.cultivation_service is None:
            await adapter.reply_text("修炼服务未初始化。")
            return

        result = await self.cultivation_service.end_seclusion(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"出关失败：{result.reason}")
            return

        await adapter.reply_text(
            f"出关成功！闭关 {result.elapsed_minutes} 分钟，获得修为 {result.exp_gained}。"
        )

    async def _start_hunt(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.cultivation_service is None:
            await adapter.reply_text("修炼服务未初始化。")
            return

        minutes = self._parse_minutes(text, "#降妖", 30)
        result = await self.cultivation_service.start_hunt(user_id, minutes)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法降妖：{result.reason}")
            return

        await adapter.reply_text(f"开始降妖 {result.elapsed_minutes} 分钟，祝道友斩妖除魔。")

    async def _end_hunt(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.cultivation_service is None:
            await adapter.reply_text("修炼服务未初始化。")
            return

        result = await self.cultivation_service.end_hunt(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"降妖归来失败：{result.reason}")
            return

        await adapter.reply_text(
            f"降妖归来！历时 {result.elapsed_minutes} 分钟，获得血气 {result.blood_qi_gained}。"
        )

    def _format_player_info(self, player: dict) -> str:
        name = player.get("name", "无名")
        level_id = player.get("level_id", 1)
        level_name = (
            self.level_data.get_cultivation_name(level_id)
            if self.level_data
            else f"练气 {level_id} 层"
        )
        exp = player.get("exp", 0)
        spirit_stones = player.get("spirit_stones", 0)
        current_hp = player.get("current_hp", 0)
        shouyuan = player.get("shouyuan", 0)
        linggen = player.get("linggen", {})
        evaluation = player.get("talent_evaluation", "未知")

        return (
            f"【{name}】\n"
            f"境界：{level_name}\n"
            f"修为：{exp}\n"
            f"灵石：{spirit_stones}\n"
            f"血量：{current_hp}\n"
            f"寿元：{shouyuan}\n"
            f"灵根：{linggen.get('type', '未知')}\n"
            f"天资：{evaluation}"
        )

    def _format_physique_info(self, player: dict) -> str:
        name = player.get("name", "无名")
        physique_id = player.get("physique_id", 1)
        physique_name = (
            self.level_data.get_physique_name(physique_id)
            if self.level_data
            else f"炼体 {physique_id} 层"
        )
        blood_qi = player.get("blood_qi", 0)
        current_hp = player.get("current_hp", 0)
        shouyuan = player.get("shouyuan", 0)

        return (
            f"【{name} · 炼体】\n"
            f"炼体境界：{physique_name}\n"
            f"血气：{blood_qi}\n"
            f"血量：{current_hp}\n"
            f"寿元：{shouyuan}"
        )

    def _format_full_info(self, player: dict) -> str:
        name = player.get("name", "无名")
        sex_value = player.get("sex", 0)
        sex = {0: "未设置", 1: "女", 2: "男"}.get(sex_value, "未知")
        level_id = player.get("level_id", 1)
        level_name = (
            self.level_data.get_cultivation_name(level_id)
            if self.level_data
            else f"练气 {level_id} 层"
        )
        physique_id = player.get("physique_id", 1)
        physique_name = (
            self.level_data.get_physique_name(physique_id)
            if self.level_data
            else f"炼体 {physique_id} 层"
        )
        exp = player.get("exp", 0)
        blood_qi = player.get("blood_qi", 0)
        spirit_stones = player.get("spirit_stones", 0)
        source_stones = player.get("source_stones", 0)
        current_hp = player.get("current_hp", 0)
        shouyuan = player.get("shouyuan", 0)
        linggen = player.get("linggen", {})
        evaluation = player.get("talent_evaluation", "未知")
        motto = player.get("motto", "暂无")

        return (
            f"【{name}】\n"
            f"性别：{sex}\n"
            f"练气境界：{level_name}\n"
            f"炼体境界：{physique_name}\n"
            f"修为：{exp}\n"
            f"血气：{blood_qi}\n"
            f"灵石：{spirit_stones}\n"
            f"源石：{source_stones}\n"
            f"血量：{current_hp}\n"
            f"寿元：{shouyuan}\n"
            f"灵根：{linggen.get('type', '未知')}\n"
            f"天资：{evaluation}\n"
            f"道宣：{motto}"
        )

    async def _show_tianjiao_list(self, adapter) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return
        await adapter.reply_text(await self.tianjiao_service.list_tianjiao_text())

    async def _show_tianjiao_status(self, adapter, text: str) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return

        name = text[len("#天骄状态"):].strip()
        await adapter.reply_text(await self.tianjiao_service.show_status_text(name))

    async def _challenge_tianjiao(self, adapter, text: str) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        name = text[len("#讨伐天骄"):].strip()
        result = await self.tianjiao_service.challenge(user_id, name)

        lines = [result.message]
        if result.details:
            lines.extend(result.details)
        await adapter.reply_text("\n".join(lines))

    async def _show_tianjiao_damage_list(self, adapter, text: str) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return

        name = text[len("#天骄贡献榜"):].strip()
        await adapter.reply_text(await self.tianjiao_service.show_damage_list_text(name))

    async def _init_tianjiao(self, adapter) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return

        await self.tianjiao_service.init_all()
        await adapter.reply_text("所有天骄已初始化，可以开始挑战！")

    async def _close_tianjiao(self, adapter) -> None:
        if self.tianjiao_service is None:
            await adapter.reply_text("天骄服务未初始化。")
            return

        await self.tianjiao_service.init_all()
        await adapter.reply_text("天骄挑战已关闭并重置。")

    async def _show_secret_places(self, adapter) -> None:
        if self.exploration_data is None:
            await adapter.reply_text("探索数据未初始化。")
            return

        places = self.exploration_data.get_secret_places()
        lines = ["【秘境列表】"]
        for place in places[:20]:
            lines.append(
                f"{place.get('name')} | 灵石：{place.get('Price', 0)} | 寿元：{place.get('shouyuan', 0)}"
            )
        if len(places) > 20:
            lines.append(f"……共 {len(places)} 处，仅展示前 20 处")
        await adapter.reply_text("\n".join(lines))

    async def _start_secret_place(self, adapter, text: str) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        place_name = text[len("#降临秘境"):].strip()
        result = await self.exploration_service.start_secret_place(user_id, place_name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法降临秘境：{result.reason}")
            return

        lines = [result.message]
        if result.details:
            lines.extend(result.details)
        await adapter.reply_text("\n\n".join(lines))

    async def _show_forbidden_areas(self, adapter) -> None:
        if self.exploration_data is None:
            await adapter.reply_text("探索数据未初始化。")
            return

        areas = self.exploration_data.get_forbidden_areas()
        lines = ["【禁地列表】"]
        for area in areas[:20]:
            lines.append(
                f"{area.get('name')} | 灵石：{area.get('Price', 0)} | 修为：{area.get('experience', 0)} | 寿元：{area.get('shouyuan', 0)}"
            )
        if len(areas) > 20:
            lines.append(f"……共 {len(areas)} 处，仅展示前 20 处")
        await adapter.reply_text("\n".join(lines))

    async def _start_forbidden_area(self, adapter, text: str) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        place_name = text[len("#前往禁地"):].strip()
        result = await self.exploration_service.start_forbidden_area(user_id, place_name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法前往禁地：{result.reason}")
            return

        lines = [result.message]
        if result.details:
            lines.extend(result.details)
        await adapter.reply_text("\n\n".join(lines))

    async def _show_time_places(self, adapter) -> None:
        if self.exploration_data is None:
            await adapter.reply_text("探索数据未初始化。")
            return

        places = self.exploration_data.get_time_places()
        lines = ["【限定仙府】"]
        for place in places[:20]:
            lines.append(
                f"{place.get('name')} | 灵石：{place.get('Price', 0)}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _start_time_place(self, adapter) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        result = await self.exploration_service.start_time_place(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法探索仙府：{result.reason}")
            return

        lines = [result.message]
        if result.details:
            lines.extend(result.details)
        await adapter.reply_text("\n\n".join(lines))

    async def _show_fairy_realms(self, adapter) -> None:
        if self.exploration_data is None:
            await adapter.reply_text("探索数据未初始化。")
            return

        realms = self.exploration_data.get_fairy_realms()
        lines = ["【仙境列表】"]
        for realm in realms[:20]:
            lines.append(
                f"{realm.get('name')} | 灵石：{realm.get('Price', 0)} | 寿元：{realm.get('shouyuan', 0)}"
            )
        if len(realms) > 20:
            lines.append(f"……共 {len(realms)} 处，仅展示前 20 处")
        await adapter.reply_text("\n".join(lines))

    async def _start_fairy_realm(self, adapter, text: str) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        place_name = text[len("#镇守仙境"):].strip()
        result = await self.exploration_service.start_fairy_realm(user_id, place_name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"无法镇守仙境：{result.reason}")
            return

        lines = [result.message]
        if result.details:
            lines.extend(result.details)
        await adapter.reply_text("\n\n".join(lines))

    async def _give_up(self, adapter) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        result = await self.exploration_service.give_up(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"逃离失败：{result.reason}")
            return

        await adapter.reply_text(result.message)

    async def _show_dungeon_drop(self, adapter, text: str) -> None:
        if self.exploration_service is None:
            await adapter.reply_text("探索服务未初始化。")
            return

        place_name = text[len("#副本掉落"):].strip()
        drop_text = await self.exploration_service.get_drop_text(place_name)
        await adapter.reply_text(drop_text)

    async def _rob(self, adapter) -> None:
        if self.battle_service is None:
            await adapter.reply_text("战斗服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位道友作为打劫目标。")
            return

        target_id = at_users[0]
        result = await self.battle_service.rob(user_id, target_id)

        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text("\n".join(result.messages))

    async def _duel(self, adapter) -> None:
        if self.battle_service is None:
            await adapter.reply_text("战斗服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位道友进行比武。")
            return

        target_id = at_users[0]
        result = await self.battle_service.duel(user_id, target_id)

        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text("\n".join(result.messages))

    async def _init_boss(self, adapter) -> None:
        if self.boss_service is None:
            await adapter.reply_text("妖王服务未初始化。")
            return

        result = await self.boss_service.initialize_boss()
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(
            f"妖王已开启！\n血量：{result.health}\n奖池：{result.reward} 灵石"
        )

    async def _close_boss(self, adapter) -> None:
        if self.boss_service is None:
            await adapter.reply_text("妖王服务未初始化。")
            return

        result = await self.boss_service.close_boss()
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text("妖王挑战已关闭。")

    async def _show_boss_status(self, adapter) -> None:
        if self.boss_service is None:
            await adapter.reply_text("妖王服务未初始化。")
            return

        status = await self.boss_service.get_status()
        if not status.get("alive", False):
            await adapter.reply_text("妖王未开启或正在刷新。")
            return

        await adapter.reply_text(
            f"----妖王状态----\n"
            f"血量：{status['health']} / {status['max_health']}\n"
            f"奖励：{status['reward']} 灵石"
        )

    async def _show_boss_damage_list(self, adapter) -> None:
        if self.boss_service is None:
            await adapter.reply_text("妖王服务未初始化。")
            return

        ranking = await self.boss_service.get_damage_list()
        if not ranking:
            await adapter.reply_text("还没人挑战过妖王。")
            return

        lines = ["****妖王贡献排行榜****"]
        for item in ranking:
            lines.append(
                f"第 {item['rank']} 名:\n"
                f"名号：{item['name']}\n"
                f"总伤害：{item['damage']}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _challenge_boss(self, adapter) -> None:
        if self.boss_service is None:
            await adapter.reply_text("妖王服务未初始化。")
            return

        user_id = await adapter.get_user_id()
        result = await self.boss_service.challenge(user_id)

        if not result.success:
            await adapter.reply_text(result.reason)
            return

        lines = result.messages[:]
        if result.boss_killed:
            lines.append(f"\n你对妖王造成了 {result.damage} 点伤害，并成功将其击杀！")
        else:
            lines.append(f"\n你对妖王造成了 {result.damage} 点伤害。")
        await adapter.reply_text("\n".join(lines))

    async def _show_modao_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_modao_ranking()
        await adapter.reply_text(self._format_ranking("魔道榜", ranking))

    async def _show_enhance_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_enhance_ranking()
        await adapter.reply_text(self._format_ranking("强化榜", ranking))

    async def _show_exp_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_exp_ranking()
        await adapter.reply_text(self._format_ranking("天榜", ranking))

    async def _show_spirit_stones_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_spirit_stones_ranking()
        await adapter.reply_text(self._format_ranking("灵榜", ranking))

    async def _show_fengshen_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_fengshen_ranking()
        await adapter.reply_text(self._format_ranking("封神榜", ranking))

    async def _show_zhetian_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_zhetian_ranking()
        await adapter.reply_text(self._format_ranking("遮天榜", ranking))

    async def _show_xiangu_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_xiangu_ranking()
        await adapter.reply_text(self._format_ranking("完美世界榜", ranking))

    async def _show_zhizun_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_zhizun_ranking()
        await adapter.reply_text(self._format_ranking("至尊榜", ranking))

    async def _show_zhenyao_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_zhenyao_ranking()
        await adapter.reply_text(self._format_ranking("镇妖塔榜", ranking))

    async def _show_shenpo_ranking(self, adapter) -> None:
        if self.ranking_service is None:
            await adapter.reply_text("排行榜服务未初始化。")
            return

        ranking = await self.ranking_service.get_shenpo_ranking()
        await adapter.reply_text(self._format_ranking("神魄榜", ranking))

    # ---------- 天地榜 ----------

    async def _tiandibang_register(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.register(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(result.message)

    async def _tiandibang_update(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.update_attributes(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_registered:
            await adapter.reply_text(result.message)
            return

        await adapter.reply_text("\n".join(result.lines))

    async def _tiandibang_ranking(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.my_point(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_registered:
            await adapter.reply_text(result.message)
            return

        await adapter.reply_text("\n".join(result.lines))

    async def _tiandibang_challenge(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.challenge(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_registered:
            await adapter.reply_text(result.message)
            return
        if result.no_challenges:
            await adapter.reply_text(result.message)
            return

        await adapter.reply_text("\n".join(result.lines))

    async def _tiandibang_shop(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.shop_list(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_registered:
            await adapter.reply_text(result.message)
            return

        await adapter.reply_text("\n".join(result.lines))

    async def _tiandibang_exchange(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        raw = text[len("#积分兑换"):].strip()
        parts = raw.split("*", 1)
        item_name = parts[0].strip()
        quantity = 1
        if len(parts) > 1:
            try:
                quantity = max(1, int(parts[1].strip()))
            except ValueError:
                quantity = 1

        if not item_name:
            await adapter.reply_text("格式：#积分兑换 物品名*数量")
            return

        result = await self.tiandibang_service.exchange(user_id, item_name, quantity)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_registered:
            await adapter.reply_text(result.message)
            return

        await adapter.reply_text(result.message)

    async def _tiandibang_settle(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.settle_rewards(
            user_id, self.master_ids
        )
        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _tiandibang_reset(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.tiandibang_service is None:
            await adapter.reply_text("天地榜服务未初始化。")
            return

        result = await self.tiandibang_service.reset_scores(
            user_id, self.master_ids
        )
        await adapter.reply_text(result.message)

    # ---------- 小世界 ----------
    async def _smallworld_create(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        world_name = text[len("#开辟小世界"):].strip()
        if not world_name:
            await adapter.reply_text("请为小世界命名，例如：#开辟小世界 青云界")
            return

        result = await self.smallworld_service.create_small_world(user_id, world_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_upgrade(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.upgrade_small_world(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_view(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.view_small_world(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_avatar(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.create_avatar(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(result.message)

    async def _smallworld_harvest(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.harvest_resources(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_planting_help(self, adapter) -> None:
        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        await adapter.reply_text(self.smallworld_service.planting_help())

    async def _smallworld_plant(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        seed_name = text[len("#小世界栽种"):].strip()
        result = await self.smallworld_service.plant_shenyao(user_id, seed_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_water_single(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        # 解析 #使用[道具名]浇灌[位置]
        import re
        match = re.match(
            r"^#使用\s*(草木精华露|岁月流金沙|掌天灵液)\s*(?:浇灌|催熟)?\s*(?:第)?(\d+)(?:号)?(?:作物|药田)?$",
            text,
        )
        if not match:
            await adapter.reply_text(
                "格式错误。示例：#使用草木精华露浇灌1 或 #使用掌天灵液催熟第2号作物"
            )
            return

        item_name = match.group(1)
        position = int(match.group(2))
        result = await self.smallworld_service.water_single_crop(
            user_id, item_name, position
        )
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_water_all(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.water_all_crops(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _smallworld_create_environment(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        item_name = text[2:-4].strip()  # 去掉 #使用 和 创造环境
        result = await self.smallworld_service.create_environment(user_id, item_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(result.message)

    async def _smallworld_force_ripen(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if user_id not in self.master_ids:
            await adapter.reply_text("只有主人可以执行此操作。")
            return

        if self.smallworld_service is None:
            await adapter.reply_text("小世界服务未初始化。")
            return

        result = await self.smallworld_service.force_ripen_all(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines) if result.lines else result.message)

    async def _show_lifespan(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.lifespan_service is None:
            await adapter.reply_text("寿元服务未初始化。")
            return

        lifespan = await self.lifespan_service.get_lifespan(user_id)
        if lifespan is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(f"【寿元】\n当前寿元：{lifespan}")

    async def _reduce_lifespan_manual(self, adapter, text_or_amount) -> None:
        user_id = await adapter.get_user_id()

        if user_id not in self.master_ids:
            await adapter.reply_text("只有主人可以执行此操作。")
            return

        if self.lifespan_service is None:
            await adapter.reply_text("寿元服务未初始化。")
            return

        if isinstance(text_or_amount, int):
            amount = text_or_amount
        else:
            text = text_or_amount
            amount_str = text[len("#执行寿元流逝"):].strip()
            if not amount_str:
                amount = 1000
            else:
                try:
                    amount = int(amount_str)
                    if amount <= 0:
                        await adapter.reply_text("请输入有效的寿元数量，如：#执行寿元流逝500")
                        return
                except ValueError:
                    await adapter.reply_text("请输入有效的寿元数量，如：#执行寿元流逝500")
                    return

        result = await self.lifespan_service.reduce_lifespan_manual(amount)
        await adapter.reply_text(
            "寿元流逝执行完成！\n"
            f"处理玩家总数：{result.processed}\n"
            f"跳过管理员/GM：{result.skipped_gm}\n"
            f"跳过神源封印玩家：{result.skipped_sealed}\n"
            f"高阶修士（减免）：{result.high_level_count}\n"
            f"特殊体质（减免）：{result.special_body_count}\n"
            f"耗时：{result.duration_seconds:.2f} 秒"
        )

    async def _show_yuanshen(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        result = await self.yuanshen_service.get_status(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.not_condensed:
            await adapter.reply_text(
                f"【{result.name}元神状态】\n"
                f"元神强度：{result.yuanshen}/{result.yuanshen_limit}\n"
                f"元神等级：未凝练\n"
                f"神识强度：{result.shenshi}点\n"
                f"状态：你还没有凝练元神"
            )
            return

        await adapter.reply_text(
            f"【{result.name}元神状态】\n"
            f"元神强度：{result.yuanshen}/{result.yuanshen_limit}\n"
            f"元神等级：{result.level_name}\n"
            f"神识强度：{result.shenshi}点\n"
            f"状态：已凝练"
        )

    async def _condense_yuanshen(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        result = await self.yuanshen_service.condense(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.insufficient_yuanshen:
            await adapter.reply_text(
                f"当前元神强度不足，难以凝练元神。\n"
                f"需要元神：{result.required_yuanshen}"
            )
            return

        if result.insufficient_mijing:
            await adapter.reply_text(
                f"你的秘境体系道果不够强大，需先达到秘境等级 {result.required_mijing_level}。"
            )
            return

        if result.insufficient_xiangu:
            await adapter.reply_text(
                f"你的仙古今世法道果不够强大，需先达到仙古等级 {result.required_xiangu_level}。"
            )
            return

        await adapter.reply_text(
            f"你成功凝练了元神，目前的元神级别是 {result.level_name}！"
        )

    async def _open_neijing(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        result = await self.yuanshen_service.open_neijing(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.not_condensed:
            await adapter.reply_text("你连元神都未凝练，谈何内景地？")
            return

        if result.high_level_block:
            await adapter.reply_text("你的道躯早已自成宇宙，内景地道源粒子触体即散。")
            return

        if result.already_open:
            await adapter.reply_text("你的内景地已然开启。")
            return

        if result.insufficient_yuanshen:
            await adapter.reply_text(
                f"你的元神并不足以开启内景地，需要 {result.cost} 元神。"
            )
            return

        if result.success:
            await adapter.reply_text(
                "紫府洞开，黄庭初现！\n"
                "你的思感超越了物质界限，开启了道家黄庭内景地！"
            )
        else:
            await adapter.reply_text(
                f"冲关失败，终究未能开启内景。\n"
                f"本次开启概率：{result.probability * 100:.0f}%\n"
                f"损失元神：{result.cost}"
            )

    async def _enter_neijing(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        result = await self.yuanshen_service.enter_neijing(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.high_level_block:
            await adapter.reply_text("你的道躯早已自成宇宙，内景地道源粒子触体即散。")
            return

        if result.not_open:
            await adapter.reply_text(
                "「内景未开，道门紧闭」\n需先使用 #开启内景地 方能进入。"
            )
            return

        await adapter.reply_text(
            "【内景悟道·时溯千年】\n"
            f"修为淬炼 +{result.exp_gained}\n"
            f"血气升华 +{result.blood_qi_gained}\n"
            f"神识蜕变 +{result.shenshi_gained}\n"
            f"道伤消解 -{result.daoshang_reduced:.1f}"
        )

    async def _neijing_batch(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        times_str = text[len("#内景地修炼"):].strip().lstrip("*")
        times = 1
        if times_str:
            try:
                times = int(times_str)
                if times <= 0:
                    await adapter.reply_text("次数必须≥1。")
                    return
            except ValueError:
                await adapter.reply_text("格式：#内景地修炼*10")
                return

        result = await self.yuanshen_service.neijing_batch(user_id, times)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if result.not_condensed:
            await adapter.reply_text("你连元神都未凝练，谈何内景地？")
            return

        if result.high_level_block:
            await adapter.reply_text("你的道躯早已自成宇宙，内景地道源粒子触体即散。")
            return

        summary = (
            "内景地批量修炼完成！\n"
            f"计划次数：{result.planned} 次\n"
            f"实际执行：{result.executed} 次\n"
            f"成功开启：{result.success} 次\n"
            f"失败次数：{result.failed} 次\n"
            f"累计消耗元神：{result.total_cost}\n"
        )
        if result.messages:
            summary += "\n" + "\n".join(result.messages)
        await adapter.reply_text(summary)

    # ---------- 内景地空间 ----------

    async def _open_inner_world(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        result = await self.inner_world_service.open(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(result.message)

    async def _view_inner_world(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        result = await self.inner_world_service.view(user_id)
        await adapter.reply_text(result.message)

    async def _upgrade_inner_world(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        result = await self.inner_world_service.upgrade(user_id)
        await adapter.reply_text(result.message)

    async def _store_inner_world(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        raw = text[len("#存入"):].strip()
        parts = raw.replace("*", " ").split()
        if len(parts) < 1:
            await adapter.reply_text("格式：#存入 物品名 数量\n或：#存入物品名*数量")
            return

        name = parts[0]
        quantity = "all"
        if len(parts) > 1:
            quantity = parts[1]

        result = await self.inner_world_service.store(user_id, name, quantity)
        await adapter.reply_text(result.message)

    async def _take_inner_world(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        raw = text[len("#取出"):].strip()
        parts = raw.replace("*", " ").split()
        if len(parts) < 1:
            await adapter.reply_text("格式：#取出 物品名 数量\n或：#取出物品名*数量")
            return

        name = parts[0]
        quantity = "all"
        if len(parts) > 1:
            quantity = parts[1]

        result = await self.inner_world_service.take(user_id, name, quantity)
        await adapter.reply_text(result.message)

    async def _store_all_inner_world(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        result = await self.inner_world_service.store_all(user_id)
        await adapter.reply_text(result.message)

    async def _take_all_inner_world(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        result = await self.inner_world_service.take_all(user_id)
        await adapter.reply_text(result.message)

    async def _take_category_inner_world(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inner_world_service is None:
            await adapter.reply_text("内景地空间服务未初始化。")
            return

        for prefix in ("#按类别取出", "#取出类别"):
            if text.startswith(prefix):
                category = text[len(prefix):].strip()
                break
        else:
            category = ""

        if not category:
            await adapter.reply_text("格式：#按类别取出 类别\n例如：#按类别取出 草药")
            return

        result = await self.inner_world_service.take_category(user_id, category)
        await adapter.reply_text(result.message)

    async def _show_inventory(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.inventory_service is None:
            await adapter.reply_text("纳戒服务未初始化。")
            return

        result = await self.inventory_service.view(user_id)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        lines = [
            f"【{result.name}的纳戒】",
            f"纳戒等级：{result.level}",
            f"灵石：{result.spirit_stones}/{result.spirit_stone_limit}",
        ]

        has_items = False
        for category, items in result.categories.items():
            if not items:
                continue
            has_items = True
            lines.append(f"\n【{category}】")
            for item in items:
                quantity = item.get("quantity", 1)
                name = item.get("name", "未知")
                lines.append(f"  {name} x{quantity}")

        if not has_items:
            lines.append("\n纳戒内空空如也。")

        await adapter.reply_text("\n".join(lines))

    async def _show_gongfa(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.gongfa_service is None:
            await adapter.reply_text("功法服务未初始化。")
            return

        result = await self.gongfa_service.list_learned(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.learned:
            await adapter.reply_text("【我的功法】\n你尚未学习任何功法。")
            return

        lines = ["【我的功法】"]
        for name in result.learned:
            lines.append(f"  {name}")
        await adapter.reply_text("\n".join(lines))

    async def _learn_gongfa(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.gongfa_service is None:
            await adapter.reply_text("功法服务未初始化。")
            return

        name = text[len("#学习功法"):].strip()
        if not name:
            await adapter.reply_text("格式：#学习功法 功法名")
            return

        result = await self.gongfa_service.learn(user_id, name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_found:
            await adapter.reply_text(f"功法「{result.name}」不存在，请核对名称。")
            return
        if result.already_learned:
            await adapter.reply_text(f"你已学习过功法「{result.name}」。")
            return

        await adapter.reply_text(
            f"学习成功！\n"
            f"功法：{result.name}\n"
            f"类型：{result.type}"
        )

    async def _cultivate_yuanshen_with_gongfa(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.yuanshen_service is None:
            await adapter.reply_text("元神服务未初始化。")
            return

        gongfa_name = text[1:-4].strip()
        if not gongfa_name:
            await adapter.reply_text("格式：以功法名修炼元神")
            return

        result = await self.yuanshen_service.cultivate_with_gongfa(user_id, gongfa_name)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.not_condensed:
            await adapter.reply_text("你连元神都未凝练，无法修炼元神。")
            return
        if result.unknown_gongfa:
            await adapter.reply_text(f"「{result.gongfa_name}」并非可用于修炼元神的功法。")
            return
        if result.not_learned:
            await adapter.reply_text(f"你尚未学习功法「{result.gongfa_name}」。")
            return
        if result.limit_abnormal:
            await adapter.reply_text("元神上限异常，无法修炼。")
            return
        if result.in_cooldown:
            await adapter.reply_text(
                f"「{result.gongfa_name}」正在冷却中，"
                f"剩余 {result.cooldown_remaining_minutes} 分钟。"
            )
            return

        await adapter.reply_text(
            f"以「{result.gongfa_name}」修炼元神，元神强度 +{result.yuanshen_gained}\n"
            f"当前元神：{result.current_yuanshen}/{result.yuanshen_limit}"
        )

    def _format_ranking(self, title: str, ranking: list[dict[str, Any]]) -> str:
        if not ranking:
            return f"【{title}】\n暂无数据。"

        lines = [f"【{title}】"]
        for item in ranking:
            lines.append(
                f"第 {item['rank']} 名：{item['name']}\n"
                f"  道号：{item['name']} | 数值：{item['score']}"
            )
        return "\n".join(lines)

    async def _show_linggen(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.linggen_service is None:
            await adapter.reply_text("灵根服务未初始化。")
            return

        result = await self.linggen_service.get_info(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        linggen = result.linggen
        await adapter.reply_text(
            f"【我的灵根】\n"
            f"名称：{linggen.get('name', '未知')}\n"
            f"类型：{linggen.get('type', '未知')}\n"
            f"归类：{linggen.get('归类', '未知')}\n"
            f"修炼效率：{linggen.get('eff', 1.0)}\n"
            f"生命本源：{linggen.get('生命本源', 0)}"
        )

    async def _start_elysia_ritual(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.linggen_service is None:
            await adapter.reply_text("灵根服务未初始化。")
            return

        result = await self.linggen_service.start_elysia_ritual(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.reason:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.prompt)

    async def _awaken_zhenwo(self, adapter) -> None:
        await self._awaken(adapter, "真我觉醒", self.linggen_service.awaken_zhenwo)

    async def _awaken_liuying(self, adapter) -> None:
        await self._awaken(adapter, "流萤觉醒", self.linggen_service.awaken_liuying)

    async def _awaken_shengti(self, adapter) -> None:
        await self._awaken(adapter, "圣体觉醒", self.linggen_service.awaken_shengti)

    async def _awaken_bati(self, adapter) -> None:
        await self._awaken(adapter, "霸体觉醒", self.linggen_service.awaken_bati)

    async def _awaken_yaoti(self, adapter) -> None:
        await self._awaken(adapter, "妖体觉醒", self.linggen_service.awaken_yaoti)

    async def _awaken(
        self,
        adapter,
        label: str,
        awaken_coro,
    ) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.linggen_service is None:
            await adapter.reply_text("灵根服务未初始化。")
            return

        result = await awaken_coro(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"【{label}】{result.reason}")
            return

        new_linggen = result.new_linggen
        await adapter.reply_text(
            f"【{label}】{result.message}\n"
            f"新灵根：{new_linggen.get('name')}\n"
            f"类型：{new_linggen.get('type')}"
        )

    # ---------- 宗门 ----------

    async def _list_sects(self, adapter) -> None:
        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        result = await self.sect_service.list_sects()
        if not result.sects:
            await adapter.reply_text("【宗门列表】\n暂无宗门。")
            return

        lines = ["【宗门列表】"]
        for sect in result.sects:
            lines.append(
                f"{sect['name']} | {sect['power']} | "
                f"等级{sect['level']} | {sect['members']}/{sect['limit']}人 | "
                f"入驻要求：练气{sect['min_level_id']}层"
            )
        await adapter.reply_text("\n".join(lines))

    async def _show_my_sect(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        result = await self.sect_service.get_info(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if not result.sect:
            await adapter.reply_text("你尚未加入任何宗门。")
            return

        sect = result.sect
        lines = [
            f"【{sect.get('name', '未知')}】",
            f"宗门等级：{sect.get('level', 1)}",
            f"建设等级：{sect.get('construction_level', 1)}",
            f"灵石池：{sect.get('spirit_stone_pool', 0)}",
            f"总部：{sect.get('headquarters', '暂无')}",
            f"守护神兽：{sect.get('divine_beast', '暂无')}",
        ]
        await adapter.reply_text("\n".join(lines))

    async def _join_sect(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        sect_name = text[len("#加入宗门"):].strip()
        if not sect_name:
            await adapter.reply_text("格式：#加入宗门 宗门名")
            return

        result = await self.sect_service.join(user_id, sect_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"加入宗门失败：{result.reason}")
            return

        await adapter.reply_text(result.message)

    async def _leave_sect(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        result = await self.sect_service.leave(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"退出宗门失败：{result.reason}")
            return

        await adapter.reply_text(result.message)

    async def _donate_sect(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        amount_str = text[len("#宗门捐赠"):].strip()
        try:
            amount = int(amount_str)
        except ValueError:
            await adapter.reply_text("格式：#宗门捐赠 数量")
            return

        result = await self.sect_service.donate(user_id, amount)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"捐赠失败：{result.reason}")
            return

        await adapter.reply_text(result.message)

    async def _sect_salary(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        result = await self.sect_service.salary(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(f"领取俸禄失败：{result.reason}")
            return

        await adapter.reply_text(result.message)

    async def _show_sect_donation_logs(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.sect_service is None:
            await adapter.reply_text("宗门服务未初始化。")
            return

        player = await self.player_service.load(user_id)
        if player is None:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        sect_info = player.get("sect")
        if not sect_info:
            await adapter.reply_text("你尚未加入任何宗门。")
            return

        logs = await self.sect_service.donation_logs(sect_info["name"])
        if not logs:
            await adapter.reply_text("【宗门捐献榜】\n暂无捐献记录。")
            return

        lines = ["【宗门捐献榜】"]
        for idx, log in enumerate(logs[:10], 1):
            lines.append(f"第 {idx} 名：{log['name']} | 捐献 {log['donate']} 灵石")
        await adapter.reply_text("\n".join(lines))

    # ---------- 每日任务 ----------

    async def _accept_daily_task(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daily_task_service is None:
            await adapter.reply_text("每日任务服务未初始化。")
            return

        result = await self.daily_task_service.accept(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text("每日任务接取成功！")

    async def _submit_daily_task(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daily_task_service is None:
            await adapter.reply_text("每日任务服务未初始化。")
            return

        result = await self.daily_task_service.submit(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        msg = result.message
        if result.leveled_up:
            msg += "\n每日任务等级提升！"
        await adapter.reply_text(msg)

    async def _claim_daily_task_reward(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daily_task_service is None:
            await adapter.reply_text("每日任务服务未初始化。")
            return

        result = await self.daily_task_service.claim_reward(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        msg = result.message
        if result.leveled_up:
            msg += "\n每日任务等级提升！"
        await adapter.reply_text(msg)

    # ---------- 魔头 ----------

    async def _upgrade_demon_root(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.demon_service is None:
            await adapter.reply_text("魔头服务未初始化。")
            return

        result = await self.demon_service.upgrade_demon_root(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.need_choice:
            await adapter.reply_text(result.message)
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _handle_demon_choice(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.demon_service is None:
            await adapter.reply_text("魔头服务未初始化。")
            return

        choice = "放弃魔根" if text == "#放弃魔根" else "转世魔根"
        result = await self.demon_service.handle_convert_choice(user_id, choice)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.reason and not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _enter_demon_realm(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.demon_service is None:
            await adapter.reply_text("魔头服务未初始化。")
            return

        result = await self.demon_service.enter_demon_realm(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(
            f"你堕入魔界，开始{result.action}修炼 {result.minutes} 分钟。"
        )

    async def _sacrifice_spirit_stones(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.demon_service is None:
            await adapter.reply_text("魔头服务未初始化。")
            return

        times_str = text[len("#献祭魔石"):].strip().lstrip("*")
        try:
            times = int(times_str) if times_str else 1
        except ValueError:
            await adapter.reply_text("格式：#献祭魔石*次数")
            return

        result = await self.demon_service.sacrifice_spirit_stones(user_id, times)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _cultivate_demon_art(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.demon_service is None:
            await adapter.reply_text("魔头服务未初始化。")
            return

        result = await self.demon_service.cultivate_demon_art(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(
            f"{result.message}\n获得魔道值 {result.mo_dao_gained}，修为 {result.exp_gained}"
        )

    # ---------- 洗劫 ----------

    def _parse_place_name(self, text: str, prefix: str) -> str:
        return text[len(prefix):].strip()

    async def _inspect_looting(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.looting_service is None:
            await adapter.reply_text("洗劫服务未初始化。")
            return

        place_name = self._parse_place_name(text, "#探查")
        if not place_name:
            await adapter.reply_text("格式：#探查 地点名")
            return

        result = await self.looting_service.inspect(user_id, place_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _start_looting(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.looting_service is None:
            await adapter.reply_text("洗劫服务未初始化。")
            return

        place_name = self._parse_place_name(text, "#洗劫")
        if not place_name:
            await adapter.reply_text("格式：#洗劫 地点名")
            return

        result = await self.looting_service.start(user_id, place_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _settle_looting(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.looting_service is None:
            await adapter.reply_text("洗劫服务未初始化。")
            return

        result = await self.looting_service.settle(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.no_action:
            await adapter.reply_text(result.reason)
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _reset_looting(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.looting_service is None:
            await adapter.reply_text("洗劫服务未初始化。")
            return

        place_name = self._parse_place_name(text, "#重置洗劫")
        if not place_name:
            await adapter.reply_text("格式：#重置洗劫 地点名")
            return

        result = await self.looting_service.reset(
            place_name, user_id, self.master_ids
        )
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    # ---------- 师徒 ----------

    async def _open_recruitment(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.open_recruitment(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _close_recruitment(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.close_recruitment(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _apprentice(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位道友作为师傅。")
            return

        result = await self.shitu_service.apprentice(user_id, at_users[0])
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.target_not_found:
            await adapter.reply_text("对方尚未踏入仙途。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _dissolve_shitu(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.dissolve(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _show_master_list(self, adapter) -> None:
        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.get_master_list()
        if not result.masters:
            await adapter.reply_text("【师徒列表】\n当前没有开启收徒的道友。")
            return

        lines = ["【正在收徒的道友】"]
        for master in result.masters:
            lines.append(f"{master['name']} ({master['user_id']})")
        await adapter.reply_text("\n".join(lines))

    async def _show_my_apprentice(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        apprentice = await self.shitu_service.get_my_apprentice(user_id)
        if apprentice is None:
            await adapter.reply_text("你当前没有徒弟。")
            return

        await adapter.reply_text(
            f"【我的徒弟】\n"
            f"道号：{apprentice['apprentice_name']}\n"
            f"任务阶段：{apprentice['task_stage']}/5\n"
            f"试炼Boss血量：{apprentice['boss_hp']}"
        )

    async def _show_my_master(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        master = await self.shitu_service.get_my_master(user_id)
        if master is None:
            await adapter.reply_text("你当前没有师傅。")
            return

        await adapter.reply_text(
            f"【我的师傅】\n"
            f"道号：{master['master_name']}\n"
            f"任务阶段：{master['task_stage']}/5\n"
            f"试炼Boss血量：{master['boss_hp']}"
        )

    async def _submit_shitu_task(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.submit_task(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _trial_shitu(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.trial_boss(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _show_shitu_shop(self, adapter) -> None:
        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        result = await self.shitu_service.get_shop_items()
        if not result.items:
            await adapter.reply_text("【师徒商店】\n暂无商品。")
            return

        lines = ["【师徒商店】"]
        for item in result.items:
            lines.append(f"{item.get('name')} | {item.get('积分', 0)} 积分")
        await adapter.reply_text("\n".join(lines))

    async def _exchange_shitu(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.shitu_service is None:
            await adapter.reply_text("师徒服务未初始化。")
            return

        item_name = text[len("#兑换"):].strip()
        if not item_name:
            await adapter.reply_text("格式：#兑换 物品名")
            return

        result = await self.shitu_service.exchange(user_id, item_name)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    # ---------- 轮回 ----------

    async def _reincarnate(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.reincarnation_service is None:
            await adapter.reply_text("轮回服务未初始化。")
            return

        # 若已确认，则直接执行轮回
        pending = await self.reincarnation_service.state_service.get(
            self.reincarnation_service._pending_key(user_id), 0
        )
        if pending == 1:
            result = await self.reincarnation_service.reincarnate(user_id)
            if result.player_not_found:
                await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
                return
            if not result.success:
                await adapter.reply_text(result.reason)
                return

            new_linggen = result.new_linggen
            await adapter.reply_text(
                f"{result.message}\n"
                f"新灵根：{new_linggen.get('name')}\n"
                f"类型：{new_linggen.get('type')}"
            )
            return

        result = await self.reincarnation_service.start_reincarnation(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.reason:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.prompt)

    async def _confirm_reincarnation(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.reincarnation_service is None:
            await adapter.reply_text("轮回服务未初始化。")
            return

        choice = "确认轮回" if text == "#确认轮回" else "先不轮回"
        result = await self.reincarnation_service.confirm_reincarnation(
            user_id, choice
        )
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return
        if result.reason:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text(result.message)

    async def _check_chengjiu(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.chengjiu_service is None:
            await adapter.reply_text("成就服务未初始化。")
            return

        result = await self.chengjiu_service.check(user_id)
        if result.message:
            await adapter.reply_text(result.message)
            return

        lines: list[str] = []
        if result.new:
            lines.append("恭喜获得新成就：")
            for item in result.new:
                lines.append(f"【{item.get('name')}】- {item.get('desc')}")
            lines.append("")

        percent = (
            round(result.total_unlocked / result.total_count * 100)
            if result.total_count
            else 0
        )
        lines.append(
            f"成就进度: {result.total_unlocked}/{result.total_count} ({percent}%)"
        )
        lines.append("")
        for category, data in result.by_category.items():
            lines.append(f"【{category}】: {data['unlocked']}/{data['total']}")

        await adapter.reply_text("\n".join(lines))

    async def _xiuxian_assistant(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.chengjiu_service is None:
            await adapter.reply_text("成就服务未初始化。")
            return

        result = await self.chengjiu_service.assistant(user_id)
        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text("\n".join(result.lines))

    # ---------- 仙骨金身 ----------

    async def _xiangu_breakthrough(self, adapter, extreme: bool) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.xiangu_jinshi_service is None:
            await adapter.reply_text("仙骨金身服务未初始化。")
            return

        result = await self.xiangu_jinshi_service.breakthrough(user_id, extreme=extreme)

        if result.player_not_found:
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        await adapter.reply_text(result.message)

    # ---------- 拍卖行 ----------

    async def _create_auction(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.auction_service is None:
            await adapter.reply_text("拍卖行服务未初始化。")
            return

        raw = text[len("#拍卖"):].strip()
        parts = raw.split("*")
        if len(parts) != 3:
            await adapter.reply_text("格式：#拍卖物品名*起拍价*数量")
            return

        name, price_str, qty_str = parts
        try:
            price = int(price_str)
            quantity = int(qty_str)
        except ValueError:
            await adapter.reply_text("起拍价与数量必须为整数。")
            return

        group_id = await adapter.get_group_id() or ""
        result = await self.auction_service.create_auction(
            user_id, name.strip(), price, quantity, group_id
        )
        await adapter.reply_text(result.message)

    async def _show_auction(self, adapter) -> None:
        if self.auction_service is None:
            await adapter.reply_text("拍卖行服务未初始化。")
            return

        result = await self.auction_service.get_auction()
        if result.no_auction:
            await adapter.reply_text(result.message)
            return

        auction = result.auction or {}
        bidder = auction.get("last_bidder_name") or auction.get("last_bidder_id") or "暂无"
        msg = (
            f"【当前拍卖】\n"
            f"物品：{auction.get('name')}×{auction.get('quantity')}\n"
            f"起拍价：{auction.get('start_price')}\n"
            f"当前最高价：{auction.get('last_price')}\n"
            f"最高出价者：{bidder}"
        )
        await adapter.reply_text(msg)

    async def _bid_auction(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.auction_service is None:
            await adapter.reply_text("拍卖行服务未初始化。")
            return

        price_str = text[len("#竞价"):].strip()
        price = None
        if price_str:
            try:
                price = int(price_str)
            except ValueError:
                await adapter.reply_text("出价必须为整数。")
                return

        result = await self.auction_service.bid(user_id, price)
        await adapter.reply_text(result.message)

    # ---------- 交易 ----------

    async def _create_exchange_sell(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.exchange_service is None:
            await adapter.reply_text("交易服务未初始化。")
            return

        raw = text[len("#交易"):].strip()
        parts = raw.split("*")
        if len(parts) != 3:
            await adapter.reply_text("格式：#交易物品名*数量*单价")
            return

        name, qty_str, price_str = parts
        try:
            quantity = int(qty_str)
            price = int(price_str)
        except ValueError:
            await adapter.reply_text("数量与单价必须为整数。")
            return

        result = await self.exchange_service.create_sell_listing(
            user_id, name.strip(), quantity, price
        )
        await adapter.reply_text(result.message)

    async def _show_exchange(self, adapter) -> None:
        if self.exchange_service is None:
            await adapter.reply_text("交易服务未初始化。")
            return

        result = await self.exchange_service.list_listings()
        if not result.success or not result.listings:
            await adapter.reply_text(result.message or "暂无交易挂单。")
            return

        lines = ["【交易列表】"]
        for item in result.listings:
            t = "卖" if item.get("type") == "sell" else "求购"
            lines.append(
                f"[{item.get('id', '-')}] {t} {item.get('name')}×{item.get('quantity')} "
                f"单价{item.get('price')}"
            )
        await adapter.reply_text("\n".join(lines))

    async def _buy_exchange(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.exchange_service is None:
            await adapter.reply_text("交易服务未初始化。")
            return

        raw = text[len("#购买"):].strip()
        if not raw:
            await adapter.reply_text("格式：#购买 序号 或 #购买 物品名")
            return

        result = await self.exchange_service.buy_item(user_id, raw)
        await adapter.reply_text(result.message)

    async def _create_exchange_buy(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.exchange_service is None:
            await adapter.reply_text("交易服务未初始化。")
            return

        raw = text[len("#求购"):].strip()
        parts = raw.split("*")
        if len(parts) != 3:
            await adapter.reply_text("格式：#求购物品名*数量*单价")
            return

        name, qty_str, price_str = parts
        try:
            quantity = int(qty_str)
            price = int(price_str)
        except ValueError:
            await adapter.reply_text("数量与单价必须为整数。")
            return

        result = await self.exchange_service.create_buy_request(
            user_id, name.strip(), quantity, price
        )
        await adapter.reply_text(result.message)

    async def _remove_exchange(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.exchange_service is None:
            await adapter.reply_text("交易服务未初始化。")
            return

        name = text[len("#下架"):].strip()
        if not name:
            await adapter.reply_text("格式：#下架 物品名")
            return

        result = await self.exchange_service.remove_listing(user_id, name)
        await adapter.reply_text(result.message)

    # ---------- 道侣 ----------

    async def _get_single_at(self, adapter) -> str | None:
        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位道友。")
            return None
        return at_users[0]

    async def _propose_daolv(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daolv_service is None:
            await adapter.reply_text("道侣服务未初始化。")
            return

        target_id = await self._get_single_at(adapter)
        if target_id is None:
            return

        result = await self.daolv_service.propose(user_id, target_id)
        await adapter.reply_text(result.message)

    async def _respond_daolv(self, adapter, accept: bool) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daolv_service is None:
            await adapter.reply_text("道侣服务未初始化。")
            return

        if accept:
            result = await self.daolv_service.accept(user_id)
        else:
            result = await self.daolv_service.reject(user_id)
        await adapter.reply_text(result.message)

    async def _show_daolv(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daolv_service is None:
            await adapter.reply_text("道侣服务未初始化。")
            return

        result = await self.daolv_service.get_my_daolv(user_id)
        await adapter.reply_text(result.message)

    async def _gift_daolv(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daolv_service is None:
            await adapter.reply_text("道侣服务未初始化。")
            return

        target_id = await self._get_single_at(adapter)
        if target_id is None:
            return

        result = await self.daolv_service.gift(user_id, target_id)
        await adapter.reply_text(result.message)

    async def _breakup_daolv(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.daolv_service is None:
            await adapter.reply_text("道侣服务未初始化。")
            return

        target_id = await self._get_single_at(adapter)
        if target_id is None:
            return

        result = await self.daolv_service.breakup(user_id, target_id)
        await adapter.reply_text(result.message)

    # ---------- 组队BOSS ----------

    async def _create_team_boss(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        name = text[len("#开启团本"):].strip()
        if not name:
            await adapter.reply_text("格式：#开启团本 BOSS名称")
            return

        result = await self.team_boss_service.create_boss(user_id, name)
        if result.success:
            await adapter.reply_text(
                f"团本【{result.boss_name}】已开启！HP：{result.max_hp}"
            )
        else:
            await adapter.reply_text(result.reason)

    async def _join_team_boss(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        result = await self.team_boss_service.join(user_id)
        if result.success:
            await adapter.reply_text(f"已加入团本【{result.boss_name}】")
        else:
            await adapter.reply_text(result.reason)

    async def _leave_team_boss(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        result = await self.team_boss_service.leave(user_id)
        await adapter.reply_text(result.reason if not result.success else result.message)

    async def _attack_team_boss(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        result = await self.team_boss_service.attack(user_id)
        await adapter.reply_text("\n".join(result.messages) if result.messages else result.reason)

    async def _status_team_boss(self, adapter) -> None:
        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        result = await self.team_boss_service.status()
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        boss = result.boss or {}
        lines = [
            f"【{boss.get('name', '团本')}】",
            f"HP：{boss.get('hp', 0)}/{boss.get('max_hp', 0)}",
            "伤害榜：",
        ]
        for rank in result.ranking:
            lines.append(f"{rank.get('name')}：{rank.get('damage', 0)}")
        await adapter.reply_text("\n".join(lines))

    async def _settle_team_boss(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.team_boss_service is None:
            await adapter.reply_text("组队BOSS服务未初始化。")
            return

        result = await self.team_boss_service.settle(user_id)
        if not result.success:
            await adapter.reply_text(result.reason)
            return

        await adapter.reply_text("团本结算完成！\n" + "\n".join(result.rewards))

    # ---------- 爬塔 ----------

    async def _challenge_zhenyao(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.challenge_zhenyao(user_id)
        await adapter.reply_text(result.message)

    async def _auto_challenge_zhenyao(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.auto_challenge_zhenyao(user_id)
        await adapter.reply_text(result.message)

    async def _show_zhenyao(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.get_zhenyao(user_id)
        await adapter.reply_text(result.message)

    async def _challenge_shenpo(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.challenge_shenpo(user_id)
        await adapter.reply_text(result.message)

    async def _auto_challenge_shenpo(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.auto_challenge_shenpo(user_id)
        await adapter.reply_text(result.message)

    async def _show_shenpo(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.pata_service is None:
            await adapter.reply_text("爬塔服务未初始化。")
            return

        result = await self.pata_service.get_shenpo(user_id)
        await adapter.reply_text(result.message)

    # ---------- 诸天镜 ----------

    async def _enter_zhutianjing(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.zhutianjing_service is None:
            await adapter.reply_text("诸天镜服务未初始化。")
            return

        result = await self.zhutianjing_service.enter_mirror(user_id)
        if result.success and result.lines:
            await adapter.reply_text("\n".join(result.lines))
        else:
            await adapter.reply_text(result.message)

    async def _redeem_zhutianjing(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.zhutianjing_service is None:
            await adapter.reply_text("诸天镜服务未初始化。")
            return

        target_id = await self._get_single_at(adapter)
        if target_id is None:
            return

        result = await self.zhutianjing_service.redeem(user_id, target_id)
        await adapter.reply_text(result.message)

    async def _advance_magic_girl(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.zhutianjing_service is None:
            await adapter.reply_text("诸天镜服务未初始化。")
            return

        result = await self.zhutianjing_service.advance_magic_girl(user_id)
        await adapter.reply_text(result.message)

    async def _show_zhutianjing(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.zhutianjing_service is None:
            await adapter.reply_text("诸天镜服务未初始化。")
            return

        result = await self.zhutianjing_service.get_mirror_stats(user_id)
        if result.success and result.lines:
            await adapter.reply_text("\n".join(result.lines))
        else:
            await adapter.reply_text(result.message)

    async def _draw_clow_card(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.zhutianjing_service is None:
            await adapter.reply_text("诸天镜服务未初始化。")
            return

        result = await self.zhutianjing_service.draw_clow_card(user_id)
        await adapter.reply_text(result.message)

    # ---------- 管理员/备份/运营 ----------

    async def _backup_data(self, adapter) -> None:
        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        result = await self.admin_service.backup()
        await adapter.reply_text(result.message)

    async def _restore_backup(self, adapter, text: str) -> None:
        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        filename = text[len("#恢复备份"):].strip()
        if not filename:
            await adapter.reply_text("格式：#恢复备份 文件名")
            return

        result = await self.admin_service.restore(filename)
        await adapter.reply_text(result.message)

    async def _admin_add_spirit_stones(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        at_users = await adapter.get_at_users()
        parts = text[len("#管理员加灵石"):].strip().split("*")
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位玩家并指定数量。")
            return

        try:
            amount = int(parts[-1]) if parts else 0
        except ValueError:
            await adapter.reply_text("数量必须为整数。")
            return

        result = await self.admin_service.add_spirit_stones(user_id, at_users[0], amount)
        await adapter.reply_text(result.message)

    async def _admin_add_source_stones(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        at_users = await adapter.get_at_users()
        parts = text[len("#管理员加源石"):].strip().split("*")
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位玩家并指定数量。")
            return

        try:
            amount = int(parts[-1]) if parts else 0
        except ValueError:
            await adapter.reply_text("数量必须为整数。")
            return

        result = await self.admin_service.add_source_stones(user_id, at_users[0], amount)
        await adapter.reply_text(result.message)

    async def _admin_ban(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位玩家。")
            return

        result = await self.admin_service.ban(user_id, at_users[0])
        await adapter.reply_text(result.message)

    async def _admin_unban(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        at_users = await adapter.get_at_users()
        if len(at_users) != 1:
            await adapter.reply_text("请 @ 一位玩家。")
            return

        result = await self.admin_service.unban(user_id, at_users[0])
        await adapter.reply_text(result.message)

    async def _admin_set_era(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        era_name = text[len("#设置时代"):].strip()
        if not era_name:
            await adapter.reply_text("格式：#设置时代 时代名")
            return

        result = await self.admin_service.set_era(user_id, era_name)
        await adapter.reply_text(result.message)

    async def _admin_next_era(self, adapter) -> None:
        user_id = await adapter.get_user_id()

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        result = await self.admin_service.next_era(user_id)
        await adapter.reply_text(result.message)

    async def _admin_show_era(self, adapter) -> None:
        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        result = await self.admin_service.get_era_info()
        await adapter.reply_text(result.message)

    async def _admin_auto_task(self, adapter, text: str) -> None:
        user_id = await adapter.get_user_id()

        if not await self.player_service.exists(user_id):
            await adapter.reply_text("道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")
            return

        if self.admin_service is None:
            await adapter.reply_text("管理员服务未初始化。")
            return

        arg = text[len("#自动任务"):].strip()
        enabled = arg in ("开启", "开", "on", "true", "1")
        if not enabled and arg not in ("关闭", "关", "off", "false", "0"):
            await adapter.reply_text("格式：#自动任务 开启/关闭")
            return

        result = await self.admin_service.toggle_auto_task(user_id, enabled)
        await adapter.reply_text(result.message)
