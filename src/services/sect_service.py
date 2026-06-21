from dataclasses import dataclass, field
from typing import Any

from src.data.sect_data import SectData
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class SectInfoResult:
    player_not_found: bool = False
    sect: dict[str, Any] = field(default_factory=dict)


@dataclass
class JoinSectResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class LeaveSectResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class DonateResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class SalaryResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class SectListResult:
    sects: list[dict[str, Any]] = field(default_factory=list)


class SectService:
    """宗门服务：加入、退出、捐赠、俸禄、列表。"""

    POSITION_ORDER = ["宗主", "副宗主", "长老", "内门弟子", "外门弟子"]

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        sect_data: SectData,
        random_provider=None,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.sect_data = sect_data
        self.random_provider = random_provider or __import__("random").random

    def _last_salary_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:lastsign_Asso_time"

    def _get_player_sect(self, player: dict[str, Any]) -> dict[str, Any] | None:
        return player.get("sect")

    def _set_player_sect(
        self, player: dict[str, Any], name: str, position: str
    ) -> None:
        import time
        now_ms = int(time.time() * 1000)
        player["sect"] = {
            "name": name,
            "position": position,
            "join_time": now_ms,
            "lingshi_donate": 0,
        }

    # ---------- 宗门信息 ----------

    async def get_info(self, user_id: str) -> SectInfoResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SectInfoResult(player_not_found=True)
        sect_name = player.get("sect", {}).get("name")
        if sect_name is None:
            return SectInfoResult(sect={})
        return SectInfoResult(sect=self.sect_data.get(sect_name) or {})

    # ---------- 加入宗门 ----------

    async def join(self, user_id: str, sect_name: str) -> JoinSectResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return JoinSectResult(player_not_found=True)

        if self._get_player_sect(player):
            return JoinSectResult(reason="你已加入宗门")

        sect = self.sect_data.get(sect_name)
        if sect is None:
            return JoinSectResult(reason=f"这方天地不存在{sect_name}")

        level_id = player.get("level_id", 1)
        if level_id >= 42 and sect.get("power", 0) == 0:
            return JoinSectResult(reason="仙人不可下界！")
        if level_id < 42 and sect.get("power", 0) == 1:
            return JoinSectResult(reason="你在仙界吗？就去仙界宗门")

        if level_id < sect.get("min_level_id", 1):
            return JoinSectResult(reason="境界不足，无法加入该宗门")

        limit = self.sect_data.get_member_limit(sect.get("level", 1))
        members = sect.get("members", [])
        if len(members) >= limit:
            return JoinSectResult(reason="该宗门人数已满")

        # 如果宗门没有宗主，任命为宗主；否则外门弟子
        positions = sect.get("positions", {})
        position = "宗主" if not positions.get("宗主") else "外门弟子"

        members.append(user_id)
        positions.setdefault(position, []).append(user_id)
        sect["members"] = members
        sect["positions"] = positions

        self._set_player_sect(player, sect_name, position)
        await self.player_service.save(user_id, player)

        return JoinSectResult(
            success=True,
            message=f"恭喜你成功加入{sect_name}，职位：{position}",
        )

    # ---------- 退出宗门 ----------

    async def leave(self, user_id: str, now_ms: int | None = None) -> LeaveSectResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return LeaveSectResult(player_not_found=True)

        sect_info = self._get_player_sect(player)
        if not sect_info:
            return LeaveSectResult(reason="你没有加入宗门")

        import time
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        join_time = sect_info.get("join_time", 0)
        cd_minutes = 30
        if now_ms < join_time + cd_minutes * 60 * 1000:
            remaining = (join_time + cd_minutes * 60 * 1000 - now_ms) // 60000
            return LeaveSectResult(reason=f"加入宗门不满{cd_minutes}分钟，无法退出，还剩{remaining}分钟")

        sect_name = sect_info["name"]
        position = sect_info["position"]
        sect = self.sect_data.get(sect_name)
        if sect is None:
            del player["sect"]
            await self.player_service.save(user_id, player)
            return LeaveSectResult(success=True, message="退出宗门成功")

        members = sect.get("members", [])
        positions = sect.get("positions", {})

        if position != "宗主":
            members = [m for m in members if m != user_id]
            positions[position] = [m for m in positions.get(position, []) if m != user_id]
        else:
            if len(members) < 2:
                members = []
                for pos in self.POSITION_ORDER:
                    positions[pos] = []
                message = (
                    "退出宗门成功，退出后宗门空无一人。\n"
                    "一声巨响，原本的宗门轰然倒塌，随着流沙沉没，世间再无半分痕迹"
                )
                del player["sect"]
                sect["members"] = members
                sect["positions"] = positions
                await self.player_service.save(user_id, player)
                return LeaveSectResult(success=True, message=message)
            else:
                members = [m for m in members if m != user_id]
                positions["宗主"] = []
                # 转让宗主
                for pos in self.POSITION_ORDER[1:]:
                    if positions.get(pos):
                        new_leader = positions[pos][0]
                        positions[pos] = [m for m in positions[pos] if m != new_leader]
                        positions["宗主"] = [new_leader]
                        # 更新新宗主玩家数据
                        new_leader_player = await self.player_service.load(new_leader)
                        if new_leader_player and new_leader_player.get("sect"):
                            new_leader_player["sect"]["position"] = "宗主"
                            await self.player_service.save(new_leader, new_leader_player)
                        message = f"退出宗门成功，宗主职位由{new_leader}接管"
                        break
                else:
                    message = "退出宗门成功"

        sect["members"] = members
        sect["positions"] = positions
        del player["sect"]
        player["favorability"] = 0
        await self.player_service.save(user_id, player)

        return LeaveSectResult(success=True, message=message)

    # ---------- 捐赠灵石 ----------

    async def donate(
        self, user_id: str, amount: int
    ) -> DonateResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DonateResult(player_not_found=True)

        sect_info = self._get_player_sect(player)
        if not sect_info:
            return DonateResult(reason="你没有加入宗门")

        if amount <= 0:
            return DonateResult(reason="捐赠数量必须大于0")

        if player.get("spirit_stones", 0) < amount:
            return DonateResult(reason=f"你身上只有{player['spirit_stones']}灵石，数量不足")

        sect_name = sect_info["name"]
        sect = self.sect_data.get(sect_name)
        if sect is None:
            return DonateResult(reason="宗门不存在")

        limit = self.sect_data.get_pool_limit(
            sect.get("level", 1), sect.get("power", 0)
        )
        current = sect.get("spirit_stone_pool", 0)
        if current + amount > limit:
            return DonateResult(
                reason=f"{sect_name}的灵石池最多还能容纳{limit - current}灵石"
            )

        player["spirit_stones"] = player.get("spirit_stones", 0) - amount
        sect["spirit_stone_pool"] = current + amount
        sect_info["lingshi_donate"] = sect_info.get("lingshi_donate", 0) + amount

        await self.player_service.save(user_id, player)
        return DonateResult(
            success=True,
            message=(
                f"捐赠成功，你身上还有{player['spirit_stones']}灵石，"
                f"宗门灵石池目前有{sect['spirit_stone_pool']}灵石"
            ),
        )

    # ---------- 宗门俸禄 ----------

    async def salary(self, user_id: str, now_ms: int | None = None) -> SalaryResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SalaryResult(player_not_found=True)

        sect_info = self._get_player_sect(player)
        if not sect_info:
            return SalaryResult(reason="你没有加入宗门")

        position = sect_info.get("position", "")
        if position in ("外门弟子", "内门弟子"):
            return SalaryResult(reason="没有资格领取俸禄")

        import time
        import datetime
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        today = datetime.datetime.fromtimestamp(now_ms // 1000).date()
        last_raw = await self.state_service.get(self._last_salary_key(user_id), None)
        if last_raw is not None:
            try:
                last_ms = int(last_raw)
                last_day = datetime.datetime.fromtimestamp(last_ms // 1000).date()
                if last_day == today:
                    return SalaryResult(reason="今日已经领取过了")
            except (TypeError, ValueError):
                pass

        sect_name = sect_info["name"]
        sect = self.sect_data.get(sect_name)
        if sect is None:
            return SalaryResult(reason="宗门不存在")

        multipliers = {"长老": 3, "副宗主": 4, "宗主": 5}
        n = multipliers.get(position, 1)
        fuli = sect.get("construction_level", 1) * 2000
        gift = sect.get("level", 1) * 1200 * n + fuli
        gift = gift // 2

        if sect.get("spirit_stone_pool", 0) < gift:
            return SalaryResult(reason="宗门灵石池不够发放俸禄啦，快去为宗门做贡献吧")

        sect["spirit_stone_pool"] = sect.get("spirit_stone_pool", 0) - gift
        player["spirit_stones"] = player.get("spirit_stones", 0) + gift
        await self.state_service.set(self._last_salary_key(user_id), now_ms)
        await self.player_service.save(user_id, player)

        return SalaryResult(
            success=True,
            message=f"宗门俸禄领取成功，获得了{gift}灵石",
        )

    # ---------- 宗门列表 ----------

    async def list_sects(self) -> SectListResult:
        result = []
        for name, sect in self.sect_data.sects.items():
            limit = self.sect_data.get_member_limit(sect.get("level", 1))
            result.append({
                "name": name,
                "members": len(sect.get("members", [])),
                "limit": limit,
                "power": "仙界" if sect.get("power") == 1 else "凡界",
                "level": sect.get("level", 1),
                "min_level_id": sect.get("min_level_id", 1),
                "construction_level": sect.get("construction_level", 1),
                "headquarters": sect.get("headquarters", "暂无"),
                "divine_beast": sect.get("divine_beast", "暂无"),
            })
        return SectListResult(sects=result)

    # ---------- 捐献记录 ----------

    async def donation_logs(self, sect_name: str) -> list[dict[str, Any]]:
        sect = self.sect_data.get(sect_name)
        if sect is None:
            return []
        logs = []
        for member_id in sect.get("members", []):
            player = await self.player_service.load(member_id)
            if player is None:
                continue
            member_sect = player.get("sect", {})
            if member_sect.get("name") == sect_name:
                logs.append({
                    "name": player.get("name", member_id),
                    "donate": member_sect.get("lingshi_donate", 0),
                })
        logs.sort(key=lambda x: x["donate"], reverse=True)
        return logs
