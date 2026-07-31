# -*- coding: utf-8 -*-
"""
销售提成查询系统 (Sales Commission Query System)
==========================================
Flask 单页 Web 应用，连接本地 MySQL 数据库(rzq)，
通过浏览器查询销售人员提成信息。

三大模块：
  1. 查询区域（姓名 / 工号 / 客户名称 / 月份）
  2. 汇总展示区域（总提成 + 各产品线提成）
  3. 提成明细区域（分页表格 + 排序）

启动方式:
  C:/Users/Simon/.workbuddy/binaries/python/envs/default/Scripts/python.exe D:/WorkBuddyAI/Document/commission_query_system.py
访问:
  http://127.0.0.1:5000
"""

import decimal
import datetime
from typing import Any, Dict, List, Optional

import pymysql
from flask import Flask, request, jsonify, Response

# =============================================================================
# 全局配置
# =============================================================================

DB_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "simon",
    "database": "rzq",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# 产品名称映射：原始值 -> 用户友好名称
# 注意：数据库中实际存储的是 "产品售卖"，需映射为 "售卖产品"
PRODUCT_NAME_MAP: Dict[str, str] = {
    "百度独代": "百度独代",
    "服务商": "服务商",
    "XHS投流": "小红书",
    "TT": "抖音",
    "产品售卖": "售卖产品",
    "售卖产品": "售卖产品",
}

# 用于统计的产品原始键（与 PRODUCT_NAME_MAP 对应）
PRODUCT_STATS_KEYS: List[str] = ["百度独代", "服务商", "XHS投流", "TT", "产品售卖", "售卖产品"]

app = Flask(__name__)


# =============================================================================
# 工具函数
# =============================================================================

def decode_text(val: Any) -> Any:
    """解码可能编码混乱的中文字符串。

    数据库中的中文数据存在编码混乱（latin1 存储了 gbk / utf8 字节），
    此函数尝试 latin1->gbk 和 latin1->utf8 两种解码路径，
    解码成功且包含常见中文字符则返回解码结果，否则原样返回。

    Args:
        val: 任意从数据库读取的值。

    Returns:
        解码后的字符串或原值。
    """
    if not isinstance(val, str):
        return val
    if not val:
        return val
    # 已经是正常中文则直接返回
    if any('\u4e00' <= c <= '\u9fff' for c in val):
        return val
    # 尝试 latin1 -> gbk
    try:
        decoded = val.encode('latin1').decode('gbk')
        if any('\u4e00' <= c <= '\u9fff' for c in decoded):
            return decoded
    except Exception:
        pass
    # 尝试 latin1 -> utf-8
    try:
        decoded = val.encode('latin1').decode('utf-8')
        if any('\u4e00' <= c <= '\u9fff' for c in decoded):
            return decoded
    except Exception:
        pass
    return val


def to_float(val: Any) -> float:
    """安全转换为 float，处理 None / Decimal / str。"""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def to_str(val: Any) -> str:
    """安全转换为字符串，None 返回空串。"""
    if val is None:
        return ""
    return str(val)


def format_date(val: Any) -> str:
    """格式化日期为 YYYY-MM-DD 字符串。"""
    if val is None:
        return ""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.strftime("%Y-%m-%d")
    s = str(val)
    # 截取到天
    if len(s) >= 10:
        return s[:10]
    return s


def format_month(val: Any) -> str:
    """格式化月份为 YYYY-MM 字符串。"""
    if val is None:
        return ""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.strftime("%Y-%m")
    s = str(val)
    if len(s) >= 7:
        return s[:7]
    return s


def json_safe(val: Any) -> Any:
    """将值转换为 JSON 可序列化类型。"""
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.date, datetime.datetime)):
        return format_date(val)
    if isinstance(val, bytes):
        try:
            return val.decode('utf-8')
        except Exception:
            return val.decode('latin1', errors='replace')
    return val


# =============================================================================
# 数据库连接
# =============================================================================

def get_connection() -> pymysql.connections.Connection:
    """获取 MySQL 数据库连接。"""
    return pymysql.connect(**DB_CONFIG)


# =============================================================================
# view_commission 列索引常量
#  0  核算业绩月份   date
#  1  公司名称       varchar
#  2  账户名称       varchar
#  3  产品           varchar
#  4  客户名称       varchar
#  5  部门           varchar
#  6  姓名           varchar
#  7  收款额         decimal
#  8  服务费         decimal
#  9  当月消耗       decimal
# 10  新单消耗       decimal
# 11  非新单消耗     decimal
# 12  新单利润       decimal
# 13  续费利润       decimal
# 14  新单系数       decimal
# 15  新单提成       decimal
# 16  续费系数       decimal
# 17  续费提成       decimal
# 18  毛利           decimal
# 19  绩效           decimal
# 20  管理新单提成系数 decimal
# 21  管理续费提成系数 decimal
# 22  备注           text
# 23  类型           varchar
# =============================================================================

COL_MONTH = 0
COL_COMPANY = 1
COL_ACCOUNT_NAME = 2
COL_PRODUCT = 3
COL_CLIENT_NAME = 4
COL_DEPT = 5
COL_NAME = 6
COL_RECEIPT = 7
COL_SERVICE_FEE = 8
COL_MONTHLY_CONSUME = 9
COL_NEW_CONSUME = 10
COL_NONNEW_CONSUME = 11
COL_NEW_PROFIT = 12
COL_RENEW_PROFIT = 13
COL_NEW_RATE = 14
COL_NEW_COMMISSION = 15
COL_RENEW_RATE = 16
COL_RENEW_COMMISSION = 17
COL_GROSS = 18
COL_PERF = 19
COL_MGR_NEW_RATE = 20
COL_MGR_RENEW_RATE = 21
COL_REMARK = 22
COL_TYPE = 23


def _row_value(row: Dict[str, Any], idx: int) -> Any:
    """通过列索引从 SELECT * 的字典行中取值。

    pymysql DictCursor 返回的 dict 的 key 是列名（可能乱码），
    我们将其转为 list 后按索引取值。
    """
    values = list(row.values())
    if idx < len(values):
        return values[idx]
    return None


# =============================================================================
# 业务查询
# =============================================================================

def fetch_months() -> List[str]:
    """获取 view_commission 中所有可用的月份（去重、降序）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 用 SELECT * 后取第 0 列，避免引用中文列名
            cur.execute("SELECT * FROM view_commission")
            rows = cur.fetchall()
            months_set = set()
            for row in rows:
                m = format_month(_row_value(row, COL_MONTH))
                if m:
                    months_set.add(m)
            months = sorted(months_set, reverse=True)
            return months
    finally:
        conn.close()


def fetch_client_base_map() -> Dict[str, Dict[str, Any]]:
    """从 tb_client_base 获取 account_name -> {first_consume_date, prepayment_amount} 映射。

    同时建立 client_name 的映射作为补充。
    """
    conn = get_connection()
    mapping: Dict[str, Dict[str, Any]] = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT account_name, client_name, first_consume_date, prepayment_amount "
                "FROM tb_client_base"
            )
            rows = cur.fetchall()
            for row in rows:
                acct = decode_text(row.get("account_name"))
                client = decode_text(row.get("client_name"))
                fcd = row.get("first_consume_date")
                prepay = row.get("prepayment_amount")
                entry = {
                    "first_consume_date": format_date(fcd),
                    "prepayment_amount": to_float(prepay),
                }
                if acct:
                    mapping[acct] = entry
                if client and client not in mapping:
                    mapping[client] = entry
            return mapping
    finally:
        conn.close()


def fetch_commission_records(
    name: str = "",
    emp_no: str = "",
    client_name: str = "",
    month: str = "",
) -> List[Dict[str, Any]]:
    """从 view_commission 查询提成明细记录。

    所有过滤在 Python 层完成（编码问题导致 SQL WHERE 引用中文列名不可靠）。
    需要关联 tb_jober_base_info（通过姓名匹配工号）和 tb_client_base（首消/预存款）。

    Args:
        name: 销售人员姓名（模糊）。
        emp_no: 工号（模糊）。
        client_name: 客户名称（模糊，匹配公司名称或客户名称）。
        month: 月份 YYYY-MM。

    Returns:
        处理后的记录列表。
    """
    # 1) 如果按工号查询，先从 tb_jober_base_info 找到对应姓名集合
    name_filter_set: Optional[set] = None
    if emp_no:
        name_filter_set = set()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT emp_name FROM tb_jober_base_info WHERE emp_no LIKE %s",
                    (f"%{emp_no}%",),
                )
                for row in cur.fetchall():
                    n = decode_text(row.get("emp_name"))
                    if n:
                        name_filter_set.add(n)
        finally:
            conn.close()

    # 2) 获取 tb_client_base 映射（首消日期 + 预存款）
    client_map = fetch_client_base_map()

    # 3) 全量读取 view_commission，在 Python 层过滤
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM view_commission")
            all_rows = cur.fetchall()
    finally:
        conn.close()

    # 预处理查询参数
    name_lower = name.strip().lower() if name else ""
    client_lower = client_name.strip().lower() if client_name else ""
    month_val = month.strip() if month else ""

    records: List[Dict[str, Any]] = []
    for row in all_rows:
        # 解码关键文本字段
        row_name = decode_text(_row_value(row, COL_NAME))
        row_company = decode_text(_row_value(row, COL_COMPANY))
        row_account = decode_text(_row_value(row, COL_ACCOUNT_NAME))
        row_product = decode_text(_row_value(row, COL_PRODUCT))
        row_client = decode_text(_row_value(row, COL_CLIENT_NAME))
        row_month = format_month(_row_value(row, COL_MONTH))

        # ---- 过滤 ----
        # 月份过滤
        if month_val and row_month != month_val:
            continue
        # 姓名过滤
        if name_lower:
            if not row_name or name_lower not in row_name.lower():
                continue
        # 工号过滤（通过姓名集合）
        if name_filter_set is not None:
            if not row_name or row_name not in name_filter_set:
                continue
        # 客户名称过滤（匹配公司名称或客户名称）
        if client_lower:
            matched = False
            if row_company and client_lower in row_company.lower():
                matched = True
            if row_client and client_lower in row_client.lower():
                matched = True
            if not matched:
                continue

        # ---- 计算字段 ----
        receipt = to_float(_row_value(row, COL_RECEIPT))
        service_fee = to_float(_row_value(row, COL_SERVICE_FEE))
        monthly_consume = to_float(_row_value(row, COL_MONTHLY_CONSUME))
        new_profit = to_float(_row_value(row, COL_NEW_PROFIT))
        renew_profit = to_float(_row_value(row, COL_RENEW_PROFIT))
        new_rate = to_float(_row_value(row, COL_NEW_RATE))
        new_commission = to_float(_row_value(row, COL_NEW_COMMISSION))
        renew_commission = to_float(_row_value(row, COL_RENEW_COMMISSION))
        remark = decode_text(_row_value(row, COL_REMARK))

        monthly_profit = new_profit + renew_profit
        commission_amount = new_commission + renew_commission

        # 提成系数：优先新单系数，显示为百分比
        commission_rate = new_rate

        # 产品名称映射
        product_display = PRODUCT_NAME_MAP.get(row_product, row_product)

        # 首消日期 & 预存款：先按账户名称查，再按客户名称查
        first_consume_date = ""
        prepayment_amount = 0.0
        if row_account and row_account in client_map:
            entry = client_map[row_account]
            first_consume_date = entry["first_consume_date"]
            prepayment_amount = entry["prepayment_amount"]
        elif row_client and row_client in client_map:
            entry = client_map[row_client]
            first_consume_date = entry["first_consume_date"]
            prepayment_amount = entry["prepayment_amount"]

        records.append({
            "company": to_str(row_company),
            "account_name": to_str(row_account),
            "product": to_str(product_display),
            "product_raw": to_str(row_product),
            "first_consume_date": first_consume_date,
            "receipt_amount": round(receipt, 2),
            "prepayment_amount": round(prepayment_amount, 2),
            "service_fee": round(service_fee, 2),
            "monthly_consumption": round(monthly_consume, 2),
            "monthly_profit": round(monthly_profit, 2),
            "commission_rate": round(commission_rate, 4),
            "commission_amount": round(commission_amount, 2),
            "remarks": to_str(remark),
            # 额外字段（供排序/调试）
            "_name": to_str(row_name),
            "_client": to_str(row_client),
            "_month": to_str(row_month),
        })

    return records


def compute_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据明细记录计算汇总统计。"""
    total_commission = 0.0
    baidu_commission = 0.0
    service_commission = 0.0
    xhs_commission = 0.0
    tt_commission = 0.0
    product_commission = 0.0

    for r in records:
        amt = r["commission_amount"]
        total_commission += amt
        prod = r.get("product_raw", "")
        if prod == "百度独代":
            baidu_commission += amt
        elif prod == "服务商":
            service_commission += amt
        elif prod == "XHS投流":
            xhs_commission += amt
        elif prod == "TT":
            tt_commission += amt
        elif prod in ("售卖产品", "产品售卖"):
            product_commission += amt

    return {
        "total_commission": round(total_commission, 2),
        "baidu_commission": round(baidu_commission, 2),
        "service_commission": round(service_commission, 2),
        "xhs_commission": round(xhs_commission, 2),
        "tt_commission": round(tt_commission, 2),
        "product_commission": round(product_commission, 2),
        "record_count": len(records),
    }


def fetch_suggestions(q: str) -> List[Dict[str, str]]:
    """从 tb_jober_base_info 搜索姓名/工号建议。"""
    if not q or not q.strip():
        return []
    kw = f"%{q.strip()}%"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT emp_no, emp_name FROM tb_jober_base_info "
                "WHERE emp_no LIKE %s OR emp_name LIKE %s "
                "LIMIT 20",
                (kw, kw),
            )
            rows = cur.fetchall()
            results: List[Dict[str, str]] = []
            for row in rows:
                en = decode_text(row.get("emp_name"))
                no = to_str(row.get("emp_no"))
                if en or no:
                    results.append({"emp_no": no, "emp_name": to_str(en)})
            return results
    finally:
        conn.close()


# =============================================================================
# 路由
# =============================================================================

@app.route("/")
def index() -> Response:
    """返回主页面 HTML。"""
    return Response(HTML_PAGE, mimetype="text/html")


@app.route("/api/months")
def api_months():
    """获取可用月份列表。"""
    try:
        months = fetch_months()
        return jsonify({"months": months})
    except Exception as e:
        return jsonify({"error": str(e), "months": []}), 500


@app.route("/api/search")
def api_search():
    """主查询接口。"""
    try:
        name = request.args.get("name", "").strip()
        emp_no = request.args.get("emp_no", "").strip()
        client_name = request.args.get("client_name", "").strip()
        month = request.args.get("month", "").strip()

        records = fetch_commission_records(
            name=name, emp_no=emp_no, client_name=client_name, month=month
        )
        stats = compute_stats(records)

        # 移除内部辅助字段后返回
        clean_records = []
        for r in records:
            clean = {k: v for k, v in r.items() if not k.startswith("_")}
            clean_records.append(clean)

        return jsonify({"stats": stats, "records": clean_records})
    except Exception as e:
        return jsonify({"error": str(e), "stats": {}, "records": []}), 500


@app.route("/api/suggest")
def api_suggest():
    """搜索建议接口。"""
    try:
        q = request.args.get("q", "").strip()
        results = fetch_suggestions(q)
        return jsonify({"suggestions": results})
    except Exception as e:
        return jsonify({"error": str(e), "suggestions": []}), 500


# =============================================================================
# 前端 HTML（单页应用）
# =============================================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>销售提成查询系统</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "Microsoft YaHei", "Segoe UI", Tahoma, Arial, sans-serif;
    background: #f0f2f5;
    color: #333;
    font-size: 14px;
  }
  /* 顶部标题栏 */
  .header {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    color: #fff;
    padding: 18px 32px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .header h1 { font-size: 22px; font-weight: 600; letter-spacing: 1px; }
  .header .subtitle { font-size: 12px; opacity: 0.8; margin-top: 4px; }
  .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

  /* 模块卡片通用 */
  .panel {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 20px;
    overflow: hidden;
  }
  .panel-header {
    padding: 12px 20px;
    border-bottom: 1px solid #e8e8e8;
    font-size: 15px;
    font-weight: 600;
    color: #1e3c72;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .panel-header::before {
    content: "";
    display: inline-block;
    width: 4px;
    height: 16px;
    background: #2a5298;
    border-radius: 2px;
  }
  .panel-body { padding: 20px; }

  /* 查询区域 */
  .query-form {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-end;
  }
  .form-group { display: flex; flex-direction: column; gap: 6px; }
  .form-group label { font-size: 13px; color: #666; font-weight: 500; }
  .form-group input, .form-group select {
    padding: 8px 12px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    font-size: 14px;
    min-width: 180px;
    transition: border-color 0.2s;
    outline: none;
  }
  .form-group input:focus, .form-group select:focus {
    border-color: #2a5298;
    box-shadow: 0 0 0 2px rgba(42,82,152,0.1);
  }
  .btn-query {
    background: linear-gradient(135deg, #2a5298, #1e3c72);
    color: #fff;
    border: none;
    padding: 9px 28px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    font-weight: 500;
    transition: opacity 0.2s;
    height: 38px;
  }
  .btn-query:hover { opacity: 0.9; }
  .btn-reset {
    background: #fff;
    color: #666;
    border: 1px solid #d9d9d9;
    padding: 9px 20px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    height: 38px;
  }
  .btn-reset:hover { color: #2a5298; border-color: #2a5298; }

  /* 统计卡片 */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
  }
  .stat-card {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s, box-shadow 0.15s;
  }
  .stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }
  .stat-card .stat-label {
    font-size: 13px;
    color: #888;
    margin-bottom: 8px;
  }
  .stat-card .stat-value {
    font-size: 22px;
    font-weight: 700;
    color: #1e3c72;
  }
  .stat-card.total .stat-value { color: #d4380d; }
  .stat-card.baidu .stat-value { color: #2940D3; }
  .stat-card.service .stat-value { color: #08979c; }
  .stat-card.xhs .stat-value { color: #ff4d4f; }
  .stat-card.tt .stat-value { color: #1d2129; }
  .stat-card.product .stat-value { color: #722ed1; }
  .stat-card .stat-bar {
    position: absolute;
    bottom: 0; left: 0;
    width: 100%;
    height: 3px;
  }
  .stat-card.total .stat-bar { background: #d4380d; }
  .stat-card.baidu .stat-bar { background: #2940D3; }
  .stat-card.service .stat-bar { background: #08979c; }
  .stat-card.xhs .stat-bar { background: #ff4d4f; }
  .stat-card.tt .stat-bar { background: #1d2129; }
  .stat-card.product .stat-bar { background: #722ed1; }

  /* 表格 */
  .table-wrap { overflow-x: auto; }
  table.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  table.data-table thead th {
    background: #fafafa;
    color: #555;
    font-weight: 600;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #e8e8e8;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  table.data-table thead th:hover { background: #f0f0f0; }
  table.data-table thead th .sort-icon { font-size: 10px; margin-left: 4px; color: #bbb; }
  table.data-table thead th.sorted .sort-icon { color: #2a5298; }
  table.data-table tbody td {
    padding: 9px 12px;
    border-bottom: 1px solid #f0f0f0;
    white-space: nowrap;
  }
  table.data-table tbody tr:nth-child(even) { background: #fafbfc; }
  table.data-table tbody tr:hover { background: #e6f0ff; }
  .money { color: #d4380d; font-weight: 600; font-family: "Consolas", monospace; }
  .money-blue { color: #2a5298; font-weight: 600; font-family: "Consolas", monospace; }
  .rate { color: #08979c; font-weight: 500; }
  .product-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
  }
  .tag-baidu { background: #e6ecff; color: #2940D3; }
  .tag-service { background: #e6fffb; color: #08979c; }
  .tag-xhs { background: #fff1f0; color: #ff4d4f; }
  .tag-tt { background: #f0f0f0; color: #1d2129; }
  .tag-product { background: #f9f0ff; color: #722ed1; }
  .tag-other { background: #f5f5f5; color: #666; }

  /* 分页 */
  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    border-top: 1px solid #e8e8e8;
  }
  .pagination-info { color: #888; font-size: 13px; }
  .pagination-controls { display: flex; gap: 6px; align-items: center; }
  .pagination-controls button {
    padding: 5px 12px;
    border: 1px solid #d9d9d9;
    background: #fff;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    color: #555;
    transition: all 0.15s;
  }
  .pagination-controls button:hover:not(:disabled) {
    border-color: #2a5298;
    color: #2a5298;
  }
  .pagination-controls button:disabled { opacity: 0.4; cursor: not-allowed; }
  .pagination-controls .page-info {
    padding: 5px 10px;
    font-size: 13px;
    color: #555;
  }
  .page-size-select {
    padding: 4px 8px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    font-size: 13px;
  }

  /* loading & 空状态 */
  .loading {
    text-align: center;
    padding: 40px;
    color: #999;
    font-size: 14px;
  }
  .loading .spinner {
    display: inline-block;
    width: 28px; height: 28px;
    border: 3px solid #e8e8e8;
    border-top-color: #2a5298;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 10px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty-state {
    text-align: center;
    padding: 40px;
    color: #bbb;
    font-size: 14px;
  }
  .error-msg {
    color: #ff4d4f;
    background: #fff1f0;
    border: 1px solid #ffccc7;
    border-radius: 4px;
    padding: 10px 16px;
    margin: 10px 20px;
    font-size: 13px;
  }
  .record-count-badge {
    display: inline-block;
    background: #e6f0ff;
    color: #2a5298;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 8px;
  }
  /* 建议下拉 */
  .suggestions-wrapper { position: relative; }
  .suggestions-list {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: #fff;
    border: 1px solid #d9d9d9;
    border-top: none;
    border-radius: 0 0 4px 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;
    display: none;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }
  .suggestions-list.show { display: block; }
  .suggestions-list .suggestion-item {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 13px;
    border-bottom: 1px solid #f5f5f5;
  }
  .suggestions-list .suggestion-item:hover { background: #e6f0ff; }
  .suggestions-list .suggestion-item:last-child { border-bottom: none; }

  @media (max-width: 768px) {
    .query-form { flex-direction: column; align-items: stretch; }
    .form-group input, .form-group select { min-width: 100%; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
</head>
<body>

<div class="header">
  <h1>销售提成查询系统</h1>
  <div class="subtitle">Sales Commission Query System</div>
</div>

<div class="container">

  <!-- 模块1: 查询区域 -->
  <div class="panel">
    <div class="panel-header">查询条件</div>
    <div class="panel-body">
      <form class="query-form" id="queryForm" onsubmit="return false;">
        <div class="form-group">
          <label>姓名</label>
          <div class="suggestions-wrapper">
            <input type="text" id="qName" placeholder="输入销售人员姓名" autocomplete="off">
            <div class="suggestions-list" id="nameSuggestions"></div>
          </div>
        </div>
        <div class="form-group">
          <label>工号</label>
          <div class="suggestions-wrapper">
            <input type="text" id="qEmpNo" placeholder="输入工号" autocomplete="off">
            <div class="suggestions-list" id="empNoSuggestions"></div>
          </div>
        </div>
        <div class="form-group">
          <label>客户名称</label>
          <input type="text" id="qClient" placeholder="输入客户/公司名称" autocomplete="off">
        </div>
        <div class="form-group">
          <label>查询月度</label>
          <select id="qMonth">
            <option value="">全部月份</option>
          </select>
        </div>
        <div class="form-group" style="flex-direction: row; gap: 10px;">
          <button type="button" class="btn-query" onclick="doSearch()">查 询</button>
          <button type="button" class="btn-reset" onclick="doReset()">重置</button>
        </div>
      </form>
    </div>
  </div>

  <!-- 模块2: 汇总展示 -->
  <div class="panel">
    <div class="panel-header">提成汇总<span class="record-count-badge" id="countBadge" style="display:none;">0 条</span></div>
    <div class="panel-body">
      <div class="stats-grid" id="statsGrid">
        <div class="stat-card total">
          <div class="stat-label">总提成</div>
          <div class="stat-value" id="sTotal">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
        <div class="stat-card baidu">
          <div class="stat-label">百度独代提成</div>
          <div class="stat-value" id="sBaidu">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
        <div class="stat-card service">
          <div class="stat-label">服务商提成</div>
          <div class="stat-value" id="sService">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
        <div class="stat-card xhs">
          <div class="stat-label">小红书提成</div>
          <div class="stat-value" id="sXhs">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
        <div class="stat-card tt">
          <div class="stat-label">抖音提成</div>
          <div class="stat-value" id="sTt">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
        <div class="stat-card product">
          <div class="stat-label">售卖产品提成</div>
          <div class="stat-value" id="sProduct">¥0.00</div>
          <div class="stat-bar"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- 模块3: 提成明细 -->
  <div class="panel">
    <div class="panel-header">提成明细</div>
    <div id="errorContainer"></div>
    <div class="table-wrap">
      <table class="data-table" id="detailTable">
        <thead>
          <tr>
            <th data-sort="company">公司名称<span class="sort-icon">▲▼</span></th>
            <th data-sort="account_name">账户名称<span class="sort-icon">▲▼</span></th>
            <th data-sort="product">产品<span class="sort-icon">▲▼</span></th>
            <th data-sort="first_consume_date">首消日期<span class="sort-icon">▲▼</span></th>
            <th data-sort="receipt_amount">收款金额<span class="sort-icon">▲▼</span></th>
            <th data-sort="prepayment_amount">预存款<span class="sort-icon">▲▼</span></th>
            <th data-sort="service_fee">服务费<span class="sort-icon">▲▼</span></th>
            <th data-sort="monthly_consumption">当月消耗<span class="sort-icon">▲▼</span></th>
            <th data-sort="monthly_profit">当月利润<span class="sort-icon">▲▼</span></th>
            <th data-sort="commission_rate">提成系数<span class="sort-icon">▲▼</span></th>
            <th data-sort="commission_amount">提成<span class="sort-icon">▲▼</span></th>
            <th data-sort="remarks">备注<span class="sort-icon">▲▼</span></th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <tr><td colspan="12" class="empty-state">请输入查询条件后点击"查询"按钮</td></tr>
        </tbody>
      </table>
    </div>
    <div class="pagination" id="paginationBar" style="display:none;">
      <div class="pagination-info">
        共 <span id="totalRecords">0</span> 条记录，第
        <span id="curPage">1</span> / <span id="totalPages">1</span> 页
      </div>
      <div class="pagination-controls">
        <select class="page-size-select" id="pageSizeSelect">
          <option value="20">20条/页</option>
          <option value="50">50条/页</option>
          <option value="100">100条/页</option>
        </select>
        <button onclick="goPage(1)" id="btnFirst">首页</button>
        <button onclick="goPage(currentPage-1)" id="btnPrev">上一页</button>
        <span class="page-info" id="pageInfo">1 / 1</span>
        <button onclick="goPage(currentPage+1)" id="btnNext">下一页</button>
        <button onclick="goPage(totalPages)" id="btnLast">末页</button>
      </div>
    </div>
  </div>

</div>

<script>
// ============================================================================
// 全局状态
// ============================================================================
var allRecords = [];
var currentPage = 1;
var pageSize = 20;
var totalPages = 1;
var sortColumn = "";
var sortDir = "asc"; // asc | desc

// ============================================================================
// 工具函数
// ============================================================================
function fmtMoney(val) {
  var n = parseFloat(val || 0);
  return "¥" + n.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
function fmtNum(val, dec) {
  var n = parseFloat(val || 0);
  return n.toLocaleString('zh-CN', {minimumFractionDigits: dec||2, maximumFractionDigits: dec||2});
}
function fmtRate(val) {
  var n = parseFloat(val || 0);
  // 系数存储为小数(如0.1)，显示为百分比
  if (n > 0 && n < 1) { return (n * 100).toFixed(2) + "%"; }
  return n.toFixed(2) + "%";
}
function productTag(product) {
  var map = {
    "百度独代": "tag-baidu", "服务商": "tag-service",
    "小红书": "tag-xhs", "抖音": "tag-tt", "售卖产品": "tag-product"
  };
  var cls = map[product] || "tag-other";
  return '<span class="product-tag ' + cls + '">' + escapeHtml(product) + '</span>';
}
function escapeHtml(str) {
  if (str == null) return "";
  return String(str).replace(/[&<>"']/g, function(c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  });
}

// ============================================================================
// 月份加载
// ============================================================================
function loadMonths() {
  fetch("/api/months")
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var sel = document.getElementById("qMonth");
      sel.innerHTML = '<option value="">全部月份</option>';
      var months = data.months || [];
      for (var i = 0; i < months.length; i++) {
        var opt = document.createElement("option");
        opt.value = months[i];
        opt.textContent = months[i];
        sel.appendChild(opt);
      }
    })
    .catch(function(err) {
      console.error("加载月份失败:", err);
    });
}

// ============================================================================
// 查询
// ============================================================================
function doSearch() {
  var name = document.getElementById("qName").value.trim();
  var empNo = document.getElementById("qEmpNo").value.trim();
  var client = document.getElementById("qClient").value.trim();
  var month = document.getElementById("qMonth").value;

  var params = new URLSearchParams();
  if (name) params.append("name", name);
  if (empNo) params.append("emp_no", empNo);
  if (client) params.append("client_name", client);
  if (month) params.append("month", month);

  // 显示 loading
  document.getElementById("tableBody").innerHTML =
    '<tr><td colspan="12"><div class="loading"><div class="spinner"></div><div>正在查询，请稍候...</div></div></td></tr>';
  document.getElementById("errorContainer").innerHTML = "";
  document.getElementById("paginationBar").style.display = "none";

  fetch("/api/search?" + params.toString())
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) {
        document.getElementById("errorContainer").innerHTML =
          '<div class="error-msg">查询出错：' + escapeHtml(data.error) + '</div>';
        document.getElementById("tableBody").innerHTML =
          '<tr><td colspan="12" class="empty-state">查询失败</td></tr>';
        return;
      }
      allRecords = data.records || [];
      renderStats(data.stats || {});
      currentPage = 1;
      sortColumn = "";
      sortDir = "asc";
      renderTable();
    })
    .catch(function(err) {
      document.getElementById("errorContainer").innerHTML =
        '<div class="error-msg">请求失败：' + escapeHtml(String(err)) + '</div>';
      document.getElementById("tableBody").innerHTML =
        '<tr><td colspan="12" class="empty-state">请求失败</td></tr>';
    });
}

function doReset() {
  document.getElementById("qName").value = "";
  document.getElementById("qEmpNo").value = "";
  document.getElementById("qClient").value = "";
  document.getElementById("qMonth").value = "";
}

// ============================================================================
// 统计渲染
// ============================================================================
function renderStats(stats) {
  document.getElementById("sTotal").textContent = fmtMoney(stats.total_commission);
  document.getElementById("sBaidu").textContent = fmtMoney(stats.baidu_commission);
  document.getElementById("sService").textContent = fmtMoney(stats.service_commission);
  document.getElementById("sXhs").textContent = fmtMoney(stats.xhs_commission);
  document.getElementById("sTt").textContent = fmtMoney(stats.tt_commission);
  document.getElementById("sProduct").textContent = fmtMoney(stats.product_commission);

  var badge = document.getElementById("countBadge");
  badge.textContent = (stats.record_count || 0) + " 条";
  badge.style.display = "inline-block";
}

// ============================================================================
// 表格渲染（分页 + 排序）
// ============================================================================
function getSortedRecords() {
  if (!sortColumn) return allRecords;
  var arr = allRecords.slice();
  arr.sort(function(a, b) {
    var va = a[sortColumn];
    var vb = b[sortColumn];
    // 日期/字符串/数字统一比较
    if (typeof va === "number" && typeof vb === "number") {
      return sortDir === "asc" ? va - vb : vb - va;
    }
    va = (va == null ? "" : String(va)).toLowerCase();
    vb = (vb == null ? "" : String(vb)).toLowerCase();
    if (va < vb) return sortDir === "asc" ? -1 : 1;
    if (va > vb) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
  return arr;
}

function renderTable() {
  var sorted = getSortedRecords();
  totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  var start = (currentPage - 1) * pageSize;
  var pageData = sorted.slice(start, start + pageSize);

  var tbody = document.getElementById("tableBody");
  if (pageData.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="empty-state">暂无数据</td></tr>';
    document.getElementById("paginationBar").style.display = "none";
    return;
  }

  var html = "";
  for (var i = 0; i < pageData.length; i++) {
    var r = pageData[i];
    html += '<tr>';
    html += '<td>' + escapeHtml(r.company) + '</td>';
    html += '<td>' + escapeHtml(r.account_name) + '</td>';
    html += '<td>' + productTag(r.product) + '</td>';
    html += '<td>' + escapeHtml(r.first_consume_date) + '</td>';
    html += '<td class="money">' + fmtNum(r.receipt_amount) + '</td>';
    html += '<td class="money-blue">' + fmtNum(r.prepayment_amount) + '</td>';
    html += '<td class="money-blue">' + fmtNum(r.service_fee) + '</td>';
    html += '<td class="money">' + fmtNum(r.monthly_consumption) + '</td>';
    html += '<td class="money-blue">' + fmtNum(r.monthly_profit) + '</td>';
    html += '<td class="rate">' + fmtRate(r.commission_rate) + '</td>';
    html += '<td class="money">' + fmtNum(r.commission_amount) + '</td>';
    html += '<td>' + escapeHtml(r.remarks) + '</td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;

  // 分页信息
  document.getElementById("paginationBar").style.display = "flex";
  document.getElementById("totalRecords").textContent = sorted.length;
  document.getElementById("curPage").textContent = currentPage;
  document.getElementById("totalPages").textContent = totalPages;
  document.getElementById("pageInfo").textContent = currentPage + " / " + totalPages;
  document.getElementById("btnFirst").disabled = (currentPage <= 1);
  document.getElementById("btnPrev").disabled = (currentPage <= 1);
  document.getElementById("btnNext").disabled = (currentPage >= totalPages);
  document.getElementById("btnLast").disabled = (currentPage >= totalPages);

  // 排序图标
  var ths = document.querySelectorAll("#detailTable thead th");
  for (var j = 0; j < ths.length; j++) {
    ths[j].classList.remove("sorted");
    var icon = ths[j].querySelector(".sort-icon");
    if (ths[j].getAttribute("data-sort") === sortColumn) {
      ths[j].classList.add("sorted");
      icon.textContent = sortDir === "asc" ? "▲" : "▼";
    } else {
      icon.textContent = "▲▼";
    }
  }
}

function goPage(p) {
  if (p < 1 || p > totalPages) return;
  currentPage = p;
  renderTable();
}

// 排序点击
document.querySelectorAll("#detailTable thead th").forEach(function(th) {
  th.addEventListener("click", function() {
    var col = th.getAttribute("data-sort");
    if (!col) return;
    if (sortColumn === col) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortColumn = col;
      sortDir = "asc";
    }
    currentPage = 1;
    renderTable();
  });
});

// 每页条数切换
document.getElementById("pageSizeSelect").addEventListener("change", function() {
  pageSize = parseInt(this.value);
  currentPage = 1;
  renderTable();
});

// ============================================================================
// 搜索建议
// ============================================================================
var suggestTimer = null;
function setupSuggest(inputId, listId, fillField) {
  var input = document.getElementById(inputId);
  var list = document.getElementById(listId);
  input.addEventListener("input", function() {
    var q = input.value.trim();
    if (suggestTimer) clearTimeout(suggestTimer);
    if (!q) { list.classList.remove("show"); return; }
    suggestTimer = setTimeout(function() {
      fetch("/api/suggest?q=" + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(data) {
          var suggestions = data.suggestions || [];
          if (suggestions.length === 0) {
            list.classList.remove("show");
            return;
          }
          var html = "";
          for (var i = 0; i < suggestions.length; i++) {
            var s = suggestions[i];
            html += '<div class="suggestion-item" data-value="' + escapeHtml(s[fillField]) + '">'
              + escapeHtml(s.emp_name || "") + ' (' + escapeHtml(s.emp_no || "") + ')</div>';
          }
          list.innerHTML = html;
          list.classList.add("show");
          // 点击建议项
          list.querySelectorAll(".suggestion-item").forEach(function(item) {
            item.addEventListener("click", function() {
              input.value = this.getAttribute("data-value");
              list.classList.remove("show");
            });
          });
        })
        .catch(function() { list.classList.remove("show"); });
    }, 300);
  });
  // 失焦时隐藏（延迟以允许点击）
  input.addEventListener("blur", function() {
    setTimeout(function() { list.classList.remove("show"); }, 200);
  });
  input.addEventListener("focus", function() {
    if (list.children.length > 0) list.classList.add("show");
  });
}
setupSuggest("qName", "nameSuggestions", "emp_name");
setupSuggest("qEmpNo", "empNoSuggestions", "emp_no");

// 回车触发查询
document.getElementById("qName").addEventListener("keydown", function(e) {
  if (e.key === "Enter") { e.preventDefault(); doSearch(); }
});
document.getElementById("qEmpNo").addEventListener("keydown", function(e) {
  if (e.key === "Enter") { e.preventDefault(); doSearch(); }
});
document.getElementById("qClient").addEventListener("keydown", function(e) {
  if (e.key === "Enter") { e.preventDefault(); doSearch(); }
});

// ============================================================================
// 初始化
// ============================================================================
loadMonths();
</script>

</body>
</html>
"""


# =============================================================================
# 启动
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  销售提成查询系统 启动中...")
    print("  访问地址: http://127.0.0.1:5000")
    print("  数据库: rzq @ 127.0.0.1:3306")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
