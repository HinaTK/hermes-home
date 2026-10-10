# -*- coding: utf-8 -*-
"""159992 -> 589720 exit-only guard, not a broker or a fill simulator."""
import json
from copy import deepcopy


def load_policy(path):
    if not path.exists():
        return None
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not policy.get("enabled"):
        return None
    if policy.get("source") != "sz159992" or policy.get("target") != "sh589720":
        raise ValueError("迁移标的配置无效，停止生成操作建议")
    if policy.get("target_buy_enabled") and not policy.get("target_buy_authorized_by_user"):
        raise ValueError("589720迁入须先核对银河委托并单独启用，不可仅改配置开关")
    return policy


def guard_ticket(ticket, policy):
    if not policy:
        return ticket
    ticket = deepcopy(ticket)
    blocked = [a for a in ticket.get("actions", [])
               if a.get("code") in (policy["source"], policy["target"])
               and a.get("side") == "buy"
               and not (a.get("code") == policy["target"]
                        and policy.get("target_buy_enabled")
                        and policy.get("target_buy_authorized_by_user"))]
    ticket["actions"] = [a for a in ticket.get("actions", []) if a not in blocked]
    withdrawn = ticket.setdefault("withdrawal_actions", [])
    for action in blocked:
        if action not in withdrawn:
            withdrawn.append(action)
    ticket["migration"] = {"source": policy["source"], "target": policy["target"],
                           "stage": policy.get("stage"), "broker_cancel_confirmed": False}
    if ticket.get("status") == "pending" and not ticket["actions"]:
        ticket["status"] = "none"
    return ticket


def migration_note(policy):
    if not policy:
        return ""
    if policy.get("target_buy_enabled") and policy.get("target_buy_authorized_by_user"):
        lines = ["【迁移模式】589720 科创创新药ETF国泰已启用自动买入/卖出；159992 创新药ETF银华只卖不买、卖后不接回。",
                 "159992退出卖单仅是建议，先核对已有卖单、T+1可卖库存与真实可用资金；不自动撤单、不推定成交。",
                 "159992与589720共用40,000元创新药成本额度，账户10万元；现金底已降至0，买入仅受总投资上限约束；第三ETF仅研究、未授权建仓。",
                 "扩大每格资金或开第三ETF留待观察期后再讨论；现在不自动扩大单格、不新开第三ETF。"]
    else:
        lines = ["【迁移模式】159992 创新药ETF银华停止新增买入和接回；分批退出，589720 科创创新药ETF国泰待迁入。",
                 "先核对银河旧买单是否成交/撤单；本地停买不代表已撤单。若已成交，先核实代码、方向、份额、均价并入账；若未成交且仍在途，由你在银河核对后撤单。",
                 "159992退出卖单仅是建议，先核对已有卖单、T+1可卖库存与真实可用资金；不自动撤单、不推定成交。",
                 "旧单和资金核实后，复核589720实时盘口及折溢价，再给迁入分批限价建议；当前不挂589720买单，不追涨，不虚构持仓。",
                 "159992与589720共用40,000元创新药成本额度，账户10万元；现金底已降至0，买入仅受各ETF成本上限约束；第三ETF仅研究、未授权建仓。",
                 "扩大每格资金或开第三ETF留待观察期后再讨论；现在不自动扩大单格、不新开第三ETF。"]
    for action in policy.get("broker_orders_to_reconcile", []):
        lines.append(f"核对并撤销未成交旧买单：159992 {int(action['qty']):,}份 @ {float(action['price']):.3f}；如已成交先逐笔回报。")
    return "\n".join(lines)
