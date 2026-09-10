"""Built-in corpus: 12 small Chinese KB docs (customer-support / IT domain, same
domain as datasets/sample/ch54-seeds.json). Raw pages carry header/footer noise so
the Parsing and Cleaning rings have real work to do. No external downloads."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawDoc:
    doc_id: str
    source: str
    date: str
    version: int = 7
    acl: str = "internal"
    pages: list[str] = field(default_factory=list)


HEADER = "【客服知识库 · 内部资料 · 请勿外传】"

RAW_DOCS: list[RawDoc] = [
    RawDoc(
        doc_id="refund",
        source="kb_refund_policy.md",
        date="2026-06-01",
        pages=[
            f"{HEADER}\n## 退款流程\n订单签收后 7 天内可申请退款：进入订单详情页，点击「申请退款」，1-3 个工作日原路退回。\n\n## 退款到账时间\n原路退回时间以支付渠道为准：余额支付即时到账，银行卡 3-7 个工作日，第三方支付 1-3 个工作日。\n\n第 1 页 / 共 2 页 · 打印无效",
            f"{HEADER}\n## 退款审核\n客服会在 24 小时内审核退款申请；超过 48 小时未收到处理结果，可在工单中发起催单。\n\n第 2 页 / 共 2 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="return",
        source="kb_return_exchange.md",
        date="2026-06-01",
        pages=[
            f"{HEADER}\n## 退换货政策\n质量问题 15 天内可退货；非质量问题签收后 7 天内可换同款，需保持包装完好、配件齐全。\n\n## 运输损坏\n外包装完好但商品内部损坏（如屏幕裂痕），签收后 24 小时内拍照上报，按质量问题处理，可退货或换新。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="invoice",
        source="kb_invoice.md",
        date="2026-05-20",
        pages=[
            f"{HEADER}\n## 发票开具\n支持电子普通发票和增值税专用发票，下单时可选择，订单完成后 90 天内可补开。\n\n## 发票重开\n发票抬头开错可申请重开：订单完成后 30 天内，提供正确的抬头、税号与订单号，原发票作废后 3 个工作日内开出新票。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="subscription",
        source="kb_subscription_refund.md",
        date="2026-06-15",
        pages=[
            f"{HEADER}\n## 自动续费与退款\n取消订阅后不会再扣款；若取消当月仍被扣款且未使用会员权益，可在扣款后 72 小时内申请全额退款，原路退回。\n\n## 计费方案\n年付方案比月付一年累计便宜约 20%；中途从月付升级为年付，按剩余天数折算补差价，当日生效。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="price",
        source="kb_price_protection.md",
        date="2026-06-01",
        pages=[
            f"{HEADER}\n## 价保规则\n签收后 15 天内商品降价，可申请差价补偿：提供降价页面截图作为凭证，每个订单仅可申请一次，差价 3 个工作日内退回。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="coupon",
        source="kb_coupon_rules.md",
        date="2026-06-01",
        pages=[
            f"{HEADER}\n## 优惠券使用\n结算页选择可用优惠券，每单限用一张；优惠券不与积分抵扣叠加使用，过期前 7 天会在消息中心提醒。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="account",
        source="kb_account_phone.md",
        date="2026-06-10",
        pages=[
            f"{HEADER}\n## 换绑手机号\n原手机号可收验证码时：安全中心 → 账号与安全 → 换绑手机，验证旧号即可完成。\n\n## 原手机号停用\n原手机号已停用收不到验证码时，走人工申诉通道：提交本人身份证照片与新手机号，审核 1-3 个工作日，通过后自动换绑。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="crash",
        source="kb_app_crash.md",
        date="2026-06-20",
        pages=[
            f"{HEADER}\n## App 闪退排查\n更新后闪退先尝试：清除 App 缓存 → 重启手机 → 卸载重装。安卓 14 上的闪退问题已在 3.1.2 版本修复，请升级到最新版。\n\n## 日志上报\n仍闪退时：我的 → 设置 → 问题反馈 → 勾选「附带日志」，日志仅用于定位问题，不含个人数据。\n\n日志保留 7 天，过期自动删除；工单关闭后 48 小时内技术支持会电话回访。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="upload",
        source="kb_upload_attachment.md",
        date="2026-06-05",
        pages=[
            f"{HEADER}\n## 网页端上传附件\n单文件上限 50MB，超过会直接失败；上传到 90% 左右失败多为网络波动或代理拦截，建议使用最新版 Chrome 并关闭代理后重试。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="permission",
        source="kb_team_permission.md",
        date="2026-06-18",
        pages=[
            f"{HEADER}\n## 团队空间权限\n团队空间里同事看不到新建文档，通常是文档继承了创建者的「仅自己可见」设置。修复：文档右上角「共享」→ 选择「空间内成员可见」，权限立即生效。\n\n## 权限继承\n移动到团队空间的文档会继承空间默认权限；个人空间文档不会自动共享给空间成员。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="watch",
        source="kb_notification_watch.md",
        date="2026-06-12",
        pages=[
            f"{HEADER}\n## 手表消息推送\n手表收不到消息推送时：确认手机 App 为 3.2 及以上版本，手表端登录同一账号，然后在 App「设备」页断开蓝牙后重新连接，推送恢复。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
    RawDoc(
        doc_id="trial",
        source="kb_trial_upgrade.md",
        date="2026-06-01",
        pages=[
            f"{HEADER}\n## 试用与升级\n试用期 30 天，试用期内数据全部保留；试用期还剩最后 3 天时，在「订阅」页点击「升级为正式版」，无需重装，数据与配置自动继承。\n\n第 1 页 / 共 1 页 · 打印无效",
        ],
    ),
]
