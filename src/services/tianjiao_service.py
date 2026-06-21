import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.data.tianjiao_data import TianjiaoData
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class ChallengeResult:
    """讨伐天骄的结果。"""

    error: bool = False
    message: str = ""
    details: list[str] = field(default_factory=list)
    player_win: bool = False


class TianjiaoService:
    """位面天骄服务：管理天骄状态、讨伐战斗、贡献榜与奖励。"""

    USER_COOLDOWN_MS = 30 * 60 * 1000  # 30 分钟个人冷却
    TIANJIAO_REFRESH_MS = 18 * 60 * 60 * 1000  # 18 小时天骄刷新
    LEVEL_REQUIREMENT = 32  # 法身境

    def __init__(
        self,
        tianjiao_data: TianjiaoData,
        state_service: StateService,
        player_service: PlayerService,
    ):
        self.tianjiao_data = tianjiao_data
        self.state_service = state_service
        self.player_service = player_service

    def _status_key(self, name: str) -> str:
        return f"tianjiao:status:{name}"

    def _revive_key(self, name: str) -> str:
        return f"tianjiao:global:revive:{name}"

    def _damage_key(self, name: str) -> str:
        return f"tianjiao:damage:{name}"

    def _cd_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:BOSSCD"

    async def init_all(self) -> None:
        """初始化所有天骄状态并清空 CD、贡献榜。"""
        for tianjiao in self.tianjiao_data.list_tianjiao():
            name = tianjiao["名号"]
            await self.state_service.set(
                self._status_key(name), {"currentHP": 100, "isAlive": True}
            )
            await self.state_service.delete(self._revive_key(name))
            await self.state_service.delete(self._damage_key(name))

    async def get_tianjiao_status(self, name: str) -> dict[str, Any]:
        """获取天骄当前状态，不存在则初始化为满血存活。"""
        status = await self.state_service.get(self._status_key(name))
        if not status or not isinstance(status, dict):
            status = {"currentHP": 100, "isAlive": True}
            await self.state_service.set(self._status_key(name), status)
        if status.get("currentHP", 0) <= 0:
            status["currentHP"] = 100
            status["isAlive"] = True
            await self.state_service.set(self._status_key(name), status)
        return status

    async def _is_in_revive_cd(self, name: str) -> tuple[bool, str]:
        """检查天骄是否处于全局复活 CD 中。"""
        revive_time = await self.state_service.get(self._revive_key(name))
        if revive_time and isinstance(revive_time, (int, float, str)):
            try:
                revive_ms = int(revive_time)
            except (TypeError, ValueError):
                return False, ""
            import time

            now_ms = int(time.time() * 1000)
            if now_ms < revive_ms:
                remaining = revive_ms - now_ms
                hours = remaining // (60 * 60 * 1000)
                minutes = (remaining % (60 * 60 * 1000)) // (60 * 1000)
                return True, f"{hours}小时{minutes}分钟"
        return False, ""

    async def list_tianjiao_text(self) -> str:
        """返回天骄列表文本。"""
        lines = ["****位面天骄列表****"]
        for tianjiao in self.tianjiao_data.list_tianjiao():
            lines.append(f"名号: {tianjiao.get('名号', '')}")
            lines.append(f"境界: {tianjiao.get('境界', '')}")
            lines.append(
                f"位面: {self.tianjiao_data.get_location_name(tianjiao.get('位面'))}"
            )
            lines.append("-------------------")
        return "\n".join(lines)

    async def show_status_text(self, name: str) -> str:
        """返回单个或全部天骄状态文本。"""
        if not name:
            return await self.show_all_status_text()

        tianjiao = self.tianjiao_data.find_by_name(name)
        if not tianjiao:
            return f"未找到名为「{name}」的天骄"

        in_cd, remaining = await self._is_in_revive_cd(name)
        if in_cd:
            return f"{name}已被击败，将在{remaining}后刷新"

        status = await self.get_tianjiao_status(name)
        lines = [
            f"----{name}状态----",
            f"境界: {tianjiao.get('境界', '')}",
            f"位面: {self.tianjiao_data.get_location_name(tianjiao.get('位面'))}",
            f"当前血量: {status.get('currentHP', 100)}%",
            f"状态: {'存活' if status.get('isAlive', True) else '已击败'}",
        ]
        return "\n".join(lines)

    async def show_all_status_text(self) -> str:
        """返回所有天骄状态文本。"""
        lines = ["****所有天骄状态****"]
        for tianjiao in self.tianjiao_data.list_tianjiao():
            name = tianjiao.get("名号", "")
            in_cd, remaining = await self._is_in_revive_cd(name)
            location = self.tianjiao_data.get_location_name(tianjiao.get("位面"))
            lines.append(f"名号: {name}")
            lines.append(f"境界: {tianjiao.get('境界', '')}")
            lines.append(f"位面: {location}")
            if in_cd:
                lines.append(f"状态: 已击败，{remaining}后刷新")
            else:
                status = await self.get_tianjiao_status(name)
                lines.append(f"血量: {status.get('currentHP', 100)}%")
                lines.append(f"状态: {'存活' if status.get('isAlive', True) else '已击败'}")
            lines.append("-------------------")
        return "\n".join(lines)

    async def _check_user_cooldown(self, user_id: str) -> tuple[bool, str]:
        """检查玩家是否处于讨伐冷却中。"""
        last_time = await self.state_service.get(self._cd_key(user_id))
        if last_time is None:
            return False, ""
        import time

        now_ms = int(time.time() * 1000)
        try:
            last_ms = int(last_time)
        except (TypeError, ValueError):
            return False, ""
        if now_ms < last_ms + self.USER_COOLDOWN_MS:
            remaining = last_ms + self.USER_COOLDOWN_MS - now_ms
            minutes = remaining // (60 * 1000)
            seconds = (remaining % (60 * 1000)) // 1000
            return True, f"讨伐天骄冷却中，剩余时间: {minutes}分{seconds}秒"
        return False, ""

    async def challenge(self, user_id: str, name: str) -> ChallengeResult:
        """讨伐指定天骄。"""
        if not name:
            return ChallengeResult(error=True, message="请指定要讨伐的天骄名称，例如: #讨伐天骄 猪咪岁岁")

        tianjiao = self.tianjiao_data.find_by_name(name)
        if not tianjiao:
            return ChallengeResult(error=True, message=f"未找到名为「{name}」的天骄")

        in_cd, remaining = await self._is_in_revive_cd(name)
        if in_cd:
            return ChallengeResult(error=True, message=f"{name}已被击败，将在{remaining}后刷新")

        player = await self.player_service.load(user_id)
        if player is None:
            return ChallengeResult(error=True, message="道友尚未踏入仙途，请发送 #踏入仙途 创建角色。")

        # 检查冷却
        on_cooldown, cooldown_msg = await self._check_user_cooldown(user_id)
        if on_cooldown:
            return ChallengeResult(error=True, message=cooldown_msg)

        if player.get("level_id", 1) < self.LEVEL_REQUIREMENT:
            return ChallengeResult(error=True, message="你的练气境界至少达到法身境才能讨伐天骄")

        if player.get("power_place") != tianjiao.get("位面"):
            location = self.tianjiao_data.get_location_name(tianjiao.get("位面"))
            return ChallengeResult(
                error=True,
                message=f"你当前不在「{location}」，无法挑战{name}",
            )

        hp_limit = player.get("hp_limit", player.get("血量上限", player.get("current_hp", 1)))
        current_hp = player.get("current_hp", hp_limit)
        if current_hp <= hp_limit * 0.1:
            return ChallengeResult(error=True, message="还是先疗伤吧，别急着参战了")

        # 生成天骄战斗属性
        attribute_multiplier = self._calculate_multiplier(player, name)
        enemy = self._build_enemy(tianjiao, player, attribute_multiplier)

        # 战斗模拟
        player_win = self._simulate_battle(player, enemy)

        # 更新贡献值
        if player_win:
            damage_dealt = int(hp_limit * attribute_multiplier)
        else:
            damage_dealt = int(hp_limit * attribute_multiplier * 0.1)
        await self._add_damage(name, user_id, damage_dealt)

        # 更新天骄血量
        status = await self.get_tianjiao_status(name)
        if player_win:
            status["currentHP"] = max(0, status["currentHP"] - 20)
            message = f"恭喜你战胜{name}！天骄血量减少20%，当前剩余{status['currentHP']}%"
        else:
            status["currentHP"] = max(0, status["currentHP"] - 1)
            message = f"你未能战胜{name}，天骄血量减少1%，当前剩余{status['currentHP']}%"

        details: list[str] = []

        if player_win:
            details = await self._apply_win_rewards(user_id, player, tianjiao, name, status, damage_dealt)
        else:
            details = await self._apply_loss_rewards(user_id, player, name, damage_dealt)

        await self.state_service.set(self._status_key(name), status)

        # 设置全局 CD
        import time

        await self.state_service.set(self._cd_key(user_id), int(time.time() * 1000))

        return ChallengeResult(error=False, message=message, details=details, player_win=player_win)

    def _calculate_multiplier(self, player: dict[str, Any], name: str) -> int:
        """根据玩家境界计算天骄属性倍率。"""
        if name == "猪咪岁岁":
            return 5
        mijinglevel_id = player.get("mijing_level_id", 1)
        xiangu_level_id = player.get("xiangu_level_id", 1)
        if mijinglevel_id >= 12 or xiangu_level_id >= 10:
            return 5
        if mijinglevel_id < 9 and xiangu_level_id < 7:
            return -1  # 特殊：被拍死
        return 3

    def _build_enemy(
        self, tianjiao: dict[str, Any], player: dict[str, Any], multiplier: int
    ) -> dict[str, Any]:
        """基于玩家属性生成天骄战斗属性。"""
        player_attack = player.get("attack", player.get("攻击", 1))
        player_defense = player.get("defense", player.get("防御", 1))
        player_hp_limit = player.get(
            "hp_limit", player.get("血量上限", player.get("current_hp", 1))
        )
        return {
            "名号": f"{tianjiao.get('名号', '')}{'(全力状态)' if multiplier > 1 else '(压制境界)'}",
            "攻击": int(player_attack * multiplier),
            "防御": int(player_defense * multiplier),
            "当前血量": int(player_hp_limit * multiplier),
            "血量上限": int(player_hp_limit * multiplier),
            "暴击率": tianjiao.get("暴击率", 0),
            "暴击伤害": tianjiao.get("暴击伤害", 1),
            "灵根": tianjiao.get("灵根", {}),
            "法球倍率": tianjiao.get("灵根", {}).get("法球倍率", 1),
            "学习的功法": tianjiao.get("学习的功法", []),
        }

    def _simulate_battle(self, player: dict[str, Any], enemy: dict[str, Any]) -> bool:
        """简化战斗模拟：双方轮流攻击，先击败对方者获胜。"""
        player_hp = player.get("current_hp", player.get("当前血量", 1))
        player_attack = player.get("attack", player.get("攻击", 1))
        player_defense = player.get("defense", player.get("防御", 0))
        player_crit_rate = player.get("crit_rate", player.get("暴击率", 0))
        player_crit_damage = player.get("crit_damage", player.get("暴击伤害", 1.5))

        enemy_hp = enemy.get("当前血量", 1)
        enemy_attack = enemy.get("攻击", 1)
        enemy_defense = enemy.get("防御", 0)
        enemy_crit_rate = enemy.get("暴击率", 0)
        enemy_crit_damage = enemy.get("暴击伤害", 1.5)

        player_hp = max(1, player_hp)
        enemy_hp = max(1, enemy_hp)

        for _ in range(100):
            # 玩家攻击
            dmg = self._calc_damage(player_attack, enemy_defense, player_crit_rate, player_crit_damage)
            enemy_hp -= dmg
            if enemy_hp <= 0:
                return True

            # 天骄攻击
            dmg = self._calc_damage(enemy_attack, player_defense, enemy_crit_rate, enemy_crit_damage)
            player_hp -= dmg
            if player_hp <= 0:
                return False

        # 超过回合数，判定天骄胜利
        return False

    def _calc_damage(
        self, attack: int, defense: int, crit_rate: float, crit_damage: float
    ) -> int:
        """计算一次攻击伤害。"""
        base = max(1, int(attack * attack / (attack + defense)))
        if random.random() < crit_rate:
            base = int(base * crit_damage)
        return max(1, base)

    async def _add_damage(self, name: str, user_id: str, damage: int) -> None:
        """累加玩家对天骄的伤害贡献。"""
        key = self._damage_key(name)
        current = await self.state_service.get(key)
        if not isinstance(current, dict):
            current = {}
        current[user_id] = current.get(user_id, 0) + damage
        await self.state_service.set(key, current)

    async def _apply_win_rewards(
        self,
        user_id: str,
        player: dict[str, Any],
        tianjiao: dict[str, Any],
        name: str,
        status: dict[str, Any],
        damage_dealt: int,
    ) -> list[str]:
        """发放胜利奖励，处理击杀掉落与贡献榜奖励。"""
        reward = 10000
        zuizhong = (
            player.get("mijing_level_id", 1)
            + player.get("xiangu_level_id", 1)
        ) * player.get("level_id", 1) * player.get("physique_id", 1) * reward

        await self.player_service.add_spirit_stones(user_id, 15000000)
        await self.player_service.add_source_stones(user_id, 5000000)
        await self.player_service.add_exp(user_id, zuizhong)
        await self.player_service.add_blood_qi(user_id, zuizhong)

        details = [
            f"成功战胜{name}！获得奖励：",
            "灵石：1500万",
            "源石：500万",
            f"修为：{zuizhong}",
            f"血气：{zuizhong}",
        ]

        # 斗字秘：概率领悟天骄功法
        learned = player.get("learned_gongfa", player.get("学习的功法", []))
        if "斗字秘" in learned and random.random() < 0.01:
            tianjiao_skills = tianjiao.get("学习的功法", [])
            new_skills = [s for s in tianjiao_skills if s not in learned]
            if new_skills:
                new_skill = random.choice(new_skills)
                learned.append(new_skill)
                player["learned_gongfa"] = learned
                await self.player_service.save(user_id, player)
                details.append(f"【斗字秘】触发，领悟功法：{new_skill}")

        if status["currentHP"] <= 0:
            status["isAlive"] = False
            import time

            await self.state_service.set(
                self._revive_key(name), int(time.time() * 1000) + self.TIANJIAO_REFRESH_MS
            )
            details.append(f"{name}已被彻底击败，18小时后将重新出现！")

            # 普通掉落
            for item in tianjiao.get("掉落物", []):
                if random.random() < item.get("概率", 0):
                    details.append(f"{item.get('name')} x{item.get('数量', 1)}")

            # 特殊掉落
            for special in tianjiao.get("特殊掉落", []):
                if random.random() < special.get("概率", 0):
                    details.append(
                        f"特殊掉落：{special.get('name')} x{special.get('数量', 1)}"
                    )
                    effect = special.get("效果")
                    if effect:
                        details.append(f"（{effect}）")

            # 贡献榜奖励
            contribution_text = await self._distribute_contribution_rewards(
                name, tianjiao, user_id
            )
            if contribution_text:
                details.append(contribution_text)

        return details

    async def _apply_loss_rewards(
        self, user_id: str, player: dict[str, Any], name: str, damage_dealt: int
    ) -> list[str]:
        """发放失败奖励。"""
        reward = 10
        zuizhong = (
            player.get("mijing_level_id", 1)
            + player.get("xiangu_level_id", 1)
        ) * player.get("level_id", 1) * player.get("physique_id", 1) * reward

        await self.player_service.add_spirit_stones(user_id, 3000000)
        await self.player_service.add_source_stones(user_id, 1000000)
        await self.player_service.add_exp(user_id, zuizhong)
        await self.player_service.add_blood_qi(user_id, zuizhong)

        return [
            f"你与{name}激战一番，获得奖励：",
            "灵石：300万",
            "源石：100万",
            f"修为：{zuizhong}",
            f"血气：{zuizhong}",
        ]

    async def _distribute_contribution_rewards(
        self, name: str, tianjiao: dict[str, Any], killer_qq: str
    ) -> str:
        """分发贡献榜奖励并清空榜单。"""
        contributors = await self.get_damage_rankings(name)
        if not contributors:
            return ""

        lines = [f"****{name}贡献榜奖励****"]
        for i, contributor in enumerate(contributors):
            reward_count = 1
            if i == 0:
                reward_count = 3 + random.randint(0, 2)
            elif i <= 4:
                reward_count = 2 + random.randint(0, 2)
            elif i <= 9:
                reward_count = 1 + random.randint(0, 2)

            rewards = self._give_random_items(tianjiao, reward_count)
            player_name = await self._get_player_name(contributor["qq"])
            damage_display = contributor.get("damageStr", str(contributor["damage"]))
            lines.append(f"{i + 1}. {player_name} - 伤害: {damage_display}")
            if rewards:
                lines.append(f"   获得 {len(rewards)} 样物品: {'、'.join(rewards)}")
            else:
                lines.append("   获得基础奖励")

        # 击杀者额外奖励
        if random.random() < 0.5:
            extra_count = 1 + random.randint(0, 2)
            extra_rewards = self._give_random_items(tianjiao, extra_count)
            if extra_rewards:
                killer_name = await self._get_player_name(killer_qq)
                lines.append(f"击杀者{killer_name}获得额外奖励: {'、'.join(extra_rewards)}")

        await self.state_service.delete(self._damage_key(name))
        return "\n".join(lines)

    def _give_random_items(self, tianjiao: dict[str, Any], count: int) -> list[str]:
        """从天骄掉落物中随机选取奖励。"""
        drops = tianjiao.get("掉落物", [])
        if not drops:
            return []

        base_items = [item for item in drops if item.get("概率", 0) >= 0.5]
        rare_items = [item for item in drops if item.get("概率", 0) < 0.5]

        rewards: list[str] = []
        has_dropped = False

        for _ in range(count):
            pool = rare_items if random.random() < 0.7 and rare_items else base_items
            if not pool:
                pool = drops
            item = random.choice(pool)
            actual_probability = 1.0 if item.get("概率", 0) >= 0.5 else item.get("概率", 0)
            if random.random() < actual_probability:
                rewards.append(f"{item.get('name')}x{item.get('数量', 1)}")
                has_dropped = True

        if not has_dropped and base_items:
            item = random.choice(base_items)
            rewards.append(f"{item.get('name')}x{item.get('数量', 1)}（保底奖励）")

        return rewards

    async def _get_player_name(self, user_id: str) -> str:
        """读取玩家名号。"""
        player = await self.player_service.load(user_id)
        if player:
            return player.get("name", f"玩家{user_id}")
        return f"玩家{user_id}"

    async def get_damage_rankings(self, name: str) -> list[dict[str, Any]]:
        """获取指定天骄的伤害贡献榜，按伤害降序。"""
        damage_data = await self.state_service.get(self._damage_key(name))
        if not isinstance(damage_data, dict):
            return []

        contributors = []
        for qq, damage in damage_data.items():
            try:
                damage_int = int(damage)
                contributors.append({
                    "qq": qq,
                    "damage": damage_int,
                    "damageStr": str(damage_int),
                })
            except (TypeError, ValueError):
                continue

        contributors.sort(key=lambda x: x["damage"], reverse=True)
        return contributors

    async def show_damage_list_text(self, name: str) -> str:
        """返回格式化贡献榜文本。"""
        if not name:
            return "请指定要查看的天骄名称，例如: #天骄贡献榜 猪咪岁岁"

        tianjiao = self.tianjiao_data.find_by_name(name)
        if not tianjiao:
            return f"未找到名为「{name}」的天骄"

        in_cd, _ = await self._is_in_revive_cd(name)
        if in_cd:
            return f"{name}已被击败，暂无贡献数据"

        status = await self.get_tianjiao_status(name)
        if not status.get("isAlive", True):
            return f"{name}已被击败，暂无贡献数据"

        contributors = await self.get_damage_rankings(name)
        if not contributors:
            return f"{name}暂无贡献数据"

        lines = [f"****{name}贡献榜****"]
        for i, contributor in enumerate(contributors[:10]):
            player_name = await self._get_player_name(contributor["qq"])
            damage_display = contributor.get("damageStr", str(contributor["damage"]))
            lines.append(f"{i + 1}. {player_name} - 伤害: {damage_display}")

        if len(contributors) > 10:
            lines.append(f"...等{len(contributors)}位修士")

        lines.append(f"天骄当前血量: {status.get('currentHP', 100)}%")
        return "\n".join(lines)
