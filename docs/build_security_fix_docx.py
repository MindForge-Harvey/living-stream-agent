from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUTPUT = "docs/Living_Stream_Agent_安全漏洞修复说明.docx"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_table_width(table, width_dxa=9360):
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(width_dxa))
    tbl_w.set(qn("w:type"), "dxa")


def add_paragraph(doc, text="", style=None, bold_prefix=None):
    p = doc.add_paragraph(style=style)
    if bold_prefix and text.startswith(bold_prefix):
        run = p.add_run(bold_prefix)
        run.bold = True
        p.add_run(text[len(bold_prefix):])
    else:
        p.add_run(text)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item)


def add_code_block(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(line)
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(51, 51, 51)


def add_status_table(doc):
    rows = [
        ("用户弱口令", "已修复", "删除弱口令初始化和普通管理员密码登录，超级管理员强口令由 .env 管理。"),
        ("用户名/密码枚举及暴力破解", "已修复", "登录接口增加 IP/用户维度限流、失败锁定、统一错误文案和审计日志。"),
        ("/chat/api/dialogs 未授权访问", "已修复", "旧接口删除，新接口 /chat/api/conversations 全部要求 JWT，并按 token 归属校验。"),
        ("/chat/api/agent 未授权调用", "已修复", "旧接口删除，新接口 /chat/api/assistant 全部要求 JWT，并校验 dialogId 归属。"),
        ("提示词注入", "已加固", "强化系统提示、角色边界、违禁词过滤和最终内容落库过滤。"),
        ("平台入口 token 暴露", "已修复", "platformToken 下放到后端校验，前端不再硬编码或比较 token。"),
        ("管理员/超级管理员权限边界", "已修复", "普通管理员改为绑定 userId，超级管理员接口独立鉴权。"),
        ("文件上传限制", "已修复", "增加上传大小和扩展名白名单，支持 .env 控制。"),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    set_table_width(table)
    hdr = table.rows[0].cells
    for i, text in enumerate(["问题项", "状态", "修复摘要"]):
        hdr[i].text = text
        set_cell_shading(hdr[i], "F2F4F7")
        set_cell_margins(hdr[i])
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for item, status, summary in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, [item, status, summary]):
            cell.text = text
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
    return table


def build_doc():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10

    for style_name, size, color, before, after in [
        ("Heading 1", 16, "2E74B5", 16, 8),
        ("Heading 2", 13, "2E74B5", 12, 6),
        ("Heading 3", 12, "1F4D78", 8, 4),
    ]:
        style = styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    run = title.add_run("Living Stream Agent 安全漏洞修复说明")
    run.bold = True
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor.from_string("0B2545")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(14)
    r = subtitle.add_run("针对历史渗透测试问题的整改说明与验证结论")
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor.from_string("555555")

    doc.add_heading("一、修复范围", level=1)
    add_paragraph(
        doc,
        "本次修复覆盖历史安全测试中提出的弱口令、登录枚举、未授权访问、提示词注入、权限边界和文件上传限制等问题。"
    )
    add_status_table(doc)

    doc.add_heading("二、漏洞修复情况", level=1)

    sections = [
        (
            "1. 用户弱口令问题",
            "历史版本存在 test001:123456、admin:123456 等弱口令，可被用于登录系统或进入后台。",
            [
                "删除普通管理员用户名/密码登录入口 /chat/login。",
                "删除默认弱口令管理员初始化逻辑，不再初始化 admin/admin123、admin/123456 等账号。",
                "超级管理员初始密码改为通过 .env 中 SUPER_ADMIN_INITIAL_PASSWORD 配置。",
                "JWT SECRET_KEY 已改为强随机值，token 有效期由 24 小时缩短为 8 小时。",
            ],
        ),
        (
            "2. 用户名枚举、密码枚举及暴力破解风险",
            "历史登录接口缺少失败次数限制，且错误信息可能辅助枚举用户名或密码。",
            [
                "登录接口增加 IP 维度和用户维度限流。",
                "增加失败锁定机制。",
                "失败响应统一为“凭证无效或请求过于频繁”。",
                "增加认证审计日志，记录动作、用户标识、来源 IP、结果和失败原因。",
            ],
        ),
        (
            "3. /chat/api/dialogs 未授权访问",
            "历史接口未做鉴权，可通过枚举 userId 读取任意用户对话日志。",
            [
                "删除旧接口 /chat/api/dialogs。",
                "新接口改为 /chat/api/conversations，所有对话接口均要求 JWT 鉴权。",
                "后端不再信任前端传入的 userId，用户身份统一从 JWT sub 字段获取。",
                "查询对话、读取消息、删除对话、保存消息时均校验数据归属。",
                "管理员审计接口独立为 /chat/api/admin/conversations，并要求管理员 token。",
            ],
        ),
        (
            "4. /chat/api/agent 未授权调用",
            "历史接口未做鉴权，攻击者可直接发起智能体请求。",
            [
                "删除旧接口 /chat/api/agent。",
                "新智能体接口改为 /chat/api/assistant。",
                "所有智能体接口均要求 JWT 鉴权。",
                "后端不再使用请求中的 userId，身份统一从 JWT 中获取。",
                "对话历史加载前校验当前用户是否拥有该 dialogId。",
            ],
        ),
        (
            "5. 提示词注入风险",
            "大模型可能受用户输入中的提示词注入影响，出现绕过限制或输出不合规内容的风险。",
            [
                "强化系统提示词约束，禁止泄露系统提示、内部规则和安全策略。",
                "对用户输入、文件内容和历史上下文进行角色边界隔离。",
                "增加违禁词过滤机制。",
                "流式输出结束后统一进行内容过滤，落库内容使用过滤后的最终内容。",
            ],
        ),
        (
            "6. 平台入口 token 暴露风险",
            "平台入口校验若放在前端，platformToken 可能被逆向或通过前端资源泄露。",
            [
                "前端不再校验 platformToken，只负责转发平台参数。",
                "后端通过 .env 中 PLATFORM_ENTRY_TOKEN 进行校验。",
                "使用安全比较方式校验 token。",
                "平台 token 校验接口增加失败次数限制和锁定机制。",
            ],
        ),
        (
            "7. 管理员权限模型修复",
            "普通管理员曾拥有独立用户名和密码登录入口，存在弱口令和后台入口暴露风险。",
            [
                "删除 /chat/login。",
                "普通管理员不再拥有独立用户名和密码。",
                "超级管理员创建管理员并绑定平台 userId。",
                "非管理员用户不展示后台入口。",
                "管理员 token、普通用户 token、超级管理员 token 均区分使用。",
            ],
        ),
        (
            "8. 超级管理员接口安全加固",
            "超级管理员接口需要独立鉴权、限流和异常兜底。",
            [
                "超级管理员登录增加限流和失败锁定。",
                "登录失败使用统一错误文案。",
                "管理接口全部要求超级管理员 JWT。",
                "校验账号存在、启用状态和 is_superadmin。",
                "修复 token sub 格式异常可能导致 500 的问题，统一返回 401。",
            ],
        ),
        (
            "9. 文件上传限制",
            "文件上传缺少统一大小和类型限制，存在上传超大文件或非预期文件的风险。",
            [
                "增加上传大小限制，MAX_UPLOAD_BYTES 可由 .env 控制。",
                "增加允许上传扩展名白名单 ALLOWED_UPLOAD_EXTENSIONS。",
                "文件读取改为分块读取，超过限制立即拒绝。",
            ],
        ),
    ]

    for heading, problem, fixes in sections:
        doc.add_heading(heading, level=2)
        add_paragraph(doc, f"原问题：{problem}", bold_prefix="原问题：")
        add_paragraph(doc, "修复措施：", bold_prefix="修复措施：")
        add_bullets(doc, fixes)
        add_paragraph(doc, "当前状态：已修复。", bold_prefix="当前状态：")

    doc.add_heading("三、当前关键安全配置", level=1)
    add_code_block(doc, [
        "SECRET_KEY=强随机值",
        "PLATFORM_ENTRY_TOKEN=强随机值",
        "SUPER_ADMIN_INITIAL_PASSWORD=强随机值",
        "ACCESS_TOKEN_EXPIRE_MINUTES=480",
        "AUTH_RATE_LIMIT_MAX_FAILURES=5",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS=300",
        "AUTH_LOCK_SECONDS=900",
        "MAX_UPLOAD_BYTES=10485760",
        "ALLOWED_UPLOAD_EXTENSIONS=.txt,.docx,.pdf,.xlsx,.xls",
    ])

    doc.add_heading("四、接口验证结论", level=1)
    add_paragraph(doc, "当前未发现历史高危未授权接口仍然可用。")
    add_code_block(doc, [
        "GET  /chat/api/dialogs       => 404",
        "POST /chat/api/dialogs       => 405",
        "POST /chat/api/agent         => 405",
        "GET  /docs                   => 404",
        "GET  /openapi.json           => 404",
        "GET  /redoc                  => 404",
    ])
    add_paragraph(doc, "核心业务接口无 token 访问均被拒绝：")
    add_code_block(doc, [
        "/chat/api/conversations      => 403",
        "/chat/api/assistant          => 403",
        "/chat/api/memories           => 403",
        "/chat/api/export             => 403",
        "/chat/api/admin/*            => 403",
        "/api/super-admin/*           => 401/403",
    ])

    doc.add_heading("五、剩余建议", level=1)
    add_bullets(doc, [
        "/chat/api/forbidden-words/public 当前为公开接口，如违禁词策略属于敏感信息，建议改为登录后访问或完全改为后端过滤。",
        "/chat/api/templates/public 当前公开返回全局模板，如模板属于内部资产，建议改为登录后访问。",
        "/chat/api/health 当前返回组件状态，生产环境可简化为仅返回 ok。",
        "建议后续将超级管理员 token 从 localStorage 迁移到 HttpOnly + Secure + SameSite Cookie，进一步降低 XSS 窃取风险。",
    ])

    doc.add_heading("六、总体结论", level=1)
    add_paragraph(
        doc,
        "本次针对历史安全测试报告中的弱口令、暴力破解、用户枚举、未授权访问、提示词注入等问题已完成修复。"
    )
    add_paragraph(
        doc,
        "当前系统已经实现登录限流、失败锁定、统一错误提示、审计日志、JWT 鉴权、用户数据归属校验、管理员权限隔离、超级管理员权限隔离、旧危险接口删除、文件上传限制和 token 有效期收紧。历史报告中的高危未授权访问问题已不再存在。"
    )

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fr = footer.add_run("Living Stream Agent 安全整改说明")
    fr.font.size = Pt(9)
    fr.font.color.rgb = RGBColor.from_string("666666")

    doc.save(OUTPUT)


if __name__ == "__main__":
    build_doc()
