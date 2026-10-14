"""Fail closed while confirmed subledgers are not integrated with legacy planner."""
from pathlib import Path


def block_reason(book):
    home=Path(__file__).resolve().parent.parent
    confirmed=home/'cache/grid-account'
    if any((confirmed/f'confirmed-{code}.json').exists() for code in ('589720','159363')):
        return '【勿下单】已确认子账尚未接入旧自动出票链路，暂停旧账本建议；请使用已核验子账人工复核，不登记触价为成交。'
    missing=[code for code in ('sz159363','sh589720') if code not in book.get('positions',{})]
    if missing:
        return '【勿下单】旧主账本缺少ETF：'+','.join(missing)+'；拒绝按零仓位生成建议。'
    return None
