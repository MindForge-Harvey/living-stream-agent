from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

FINAL_DOCX = OUT_DIR / "直播脚本生成智能体-技术方案.docx"
ARCH_IMG = OUT_DIR / "living_stream_architecture.png"
FLOW_IMG = OUT_DIR / "living_stream_workflow.png"
CLASSIFY_IMG = OUT_DIR / "living_stream_intent_flow.png"
ARTIFACT_MD = OUT_DIR / "template-artifact.md"

FONT_PATHS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def pick_font(size: int, bold: bool = False):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_center(draw, box, text, font, fill=(30, 30, 30), spacing=4):
    x1, y1, x2, y2 = box
    max_width = max(10, (x2 - x1) - 22)
    lines = []
    for raw in text.split("\n"):
        if draw.textbbox((0, 0), raw, font=font)[2] <= max_width:
            lines.append(raw)
            continue
        current = ""
        for ch in raw:
            candidate = current + ch
            if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                lines.append(current)
                current = ch
            else:
                current = candidate
        if current:
            lines.append(current)
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = y1 + ((y2 - y1) - total_h) / 2
    for line, w, h in zip(lines, widths, heights):
        draw.text((x1 + ((x2 - x1) - w) / 2, y), line, font=font, fill=fill)
        y += h + spacing


def arrow(draw, start, end, fill=(70, 70, 70), width=3):
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    if x2 >= x1:
        pts = [(x2, y2), (x2 - 13, y2 - 7), (x2 - 13, y2 + 7)]
    else:
        pts = [(x2, y2), (x2 + 13, y2 - 7), (x2 + 13, y2 + 7)]
    draw.polygon(pts, fill=fill)


def round_box(draw, box, fill, outline=(160, 160, 160), radius=16, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def create_architecture_image():
    img = Image.new("RGB", (1700, 820), "white")
    draw = ImageDraw.Draw(img)
    title = pick_font(28)
    label = pick_font(22)
    small = pick_font(18)
    tiny = pick_font(14)

    draw.text((60, 32), "直播脚本生成智能体总体架构", font=title, fill=(30, 30, 30))
    layers = [
        (70, 110, "数据层", ["商品资料", "直播场景", "历史对话", "用户记忆", "违禁词库", "话术模板"]),
        (390, 110, "接入与解析层", ["文件上传解析", "文本清洗", "要素抽取", "上下文装配"]),
        (710, 110, "AI智能中枢层", ["意图识别", "脚本生成", "质量打分", "订正优化", "记忆管理"]),
        (1030, 110, "应用服务层", ["脚本生成", "脚本评分", "脚本订正", "对话管理", "统计导出"]),
        (1350, 110, "展示与运维层", ["React前端", "管理后台", "SSE流式输出", "容器化部署"]),
    ]
    for x, y, head, items in layers:
        round_box(draw, (x, y, x + 250, y + 520), (248, 248, 248), (210, 210, 210), 18)
        round_box(draw, (x + 18, y + 20, x + 232, y + 75), (255, 193, 7), (210, 160, 20), 12)
        draw_center(draw, (x + 18, y + 20, x + 232, y + 75), head, label)
        yy = y + 105
        for item in items:
            color = (218, 239, 255) if "AI" not in head else (232, 245, 214)
            if "数据" in head:
                color = (255, 224, 224)
            if "应用" in head or "展示" in head:
                color = (226, 244, 226)
            round_box(draw, (x + 32, yy, x + 218, yy + 50), color, (170, 190, 200), 10)
            draw_center(draw, (x + 32, yy, x + 218, yy + 50), item, small)
            yy += 68
    for sx in [320, 640, 960, 1280]:
        arrow(draw, (sx + 8, 365), (sx + 48, 365), fill=(90, 90, 90), width=4)
    round_box(draw, (430, 675, 1270, 780), (255, 247, 219), (230, 200, 120), 12)
    draw_center(
        draw,
        (450, 692, 1250, 764),
        "OpenAI兼容接口统一接入大模型能力\nFastAPI提供后端服务，MySQL持久化业务数据",
        tiny,
    )
    img.save(ARCH_IMG, quality=95)


def create_workflow_image():
    img = Image.new("RGB", (1500, 560), "white")
    draw = ImageDraw.Draw(img)
    title = pick_font(28)
    label = pick_font(21)
    small = pick_font(17)
    draw.text((56, 28), "直播脚本生成三步闭环流程", font=title, fill=(30, 30, 30))
    boxes = [
        ("输入资料", "商品卖点\n目标客群\n直播目标"),
        ("第一步：生成脚本", "开场钩子\n产品讲解\n互动转化\n收尾引导"),
        ("第二步：质量评估", "吸引力\n逻辑性\n感染力\n专业性"),
        ("第三步：订正优化", "补强亮点\n调整节奏\n规避违禁词\n提升转化"),
        ("流式输出", "SSE实时返回\n保存对话\n沉淀记忆"),
    ]
    x = 70
    for idx, (head, body) in enumerate(boxes):
        round_box(draw, (x, 130, x + 225, 315), (248, 248, 248), (190, 190, 190), 16)
        round_box(draw, (x + 18, 150, x + 207, 200), (255, 193, 7), (215, 165, 18), 10)
        draw_center(draw, (x + 18, 150, x + 207, 200), head, label)
        draw_center(draw, (x + 20, 218, x + 205, 297), body, small)
        if idx < len(boxes) - 1:
            arrow(draw, (x + 238, 222), (x + 288, 222), fill=(80, 80, 80), width=4)
        x += 290
    round_box(draw, (275, 382, 1225, 475), (232, 245, 255), (170, 200, 220), 14)
    draw_center(draw, (295, 397, 1205, 462), "系统自动加载最近20条对话历史与用户长期记忆\n结合违禁词过滤形成可控输出闭环", small)
    img.save(FLOW_IMG, quality=95)


def create_intent_image():
    img = Image.new("RGB", (1500, 720), "white")
    draw = ImageDraw.Draw(img)
    title = pick_font(28)
    label = pick_font(20)
    small = pick_font(17)
    draw.text((58, 28), "意图识别与工具路由机制", font=title, fill=(30, 30, 30))
    round_box(draw, (80, 135, 330, 230), (255, 247, 219), (220, 190, 90), 16)
    draw_center(draw, (80, 135, 330, 230), "用户输入\n文件/文本/上下文", label)
    round_box(draw, (475, 135, 745, 230), (218, 239, 255), (150, 185, 210), 16)
    draw_center(draw, (475, 135, 745, 230), "意图识别\n识别任务类型与参数", label)
    arrow(draw, (330, 182), (475, 182), width=4)
    intents = [
        ("generate_script", "生成直播脚本"),
        ("score_script", "脚本质量打分"),
        ("revise_script", "订正优化"),
        ("analyze_script", "结构分析"),
        ("save_memory", "保存用户记忆"),
        ("general_chat", "普通问答"),
    ]
    positions = [(900, 85), (1200, 85), (900, 225), (1200, 225), (900, 365), (1200, 365)]
    for row in range(3):
        y_mid = positions[row * 2][1] + 46
        arrow(draw, (800, y_mid), (900, y_mid), width=3)
    draw.line([(800, 131), (800, 411)], fill=(70, 70, 70), width=3)
    arrow(draw, (745, 182), (800, 182), width=4)
    for idx, ((code, desc), (x, y)) in enumerate(zip(intents, positions)):
        round_box(draw, (x, y, x + 220, y + 92), (240, 250, 232), (175, 200, 150), 12)
        draw_center(draw, (x + 12, y + 10, x + 208, y + 42), code, small)
        draw_center(draw, (x + 12, y + 48, x + 208, y + 82), desc, small)
        if idx in [0, 2, 4]:
            arrow(draw, (x + 220, y + 46), (x + 300, y + 46), width=3)
    round_box(draw, (300, 570, 1200, 665), (255, 235, 235), (220, 165, 165), 14)
    draw_center(draw, (330, 587, 1170, 648), "路由结果进入统一Agent编排层\n按任务选择生成、评分、订正、记忆或普通问答链路", small)
    img.save(CLASSIFY_IMG, quality=95)


def set_run_font(run, size=None, bold=None, color=None, font_name="Songti SC"):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_end)


def add_paragraph(doc, text="", style=None, align=None, first_line=True):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(6)
    if first_line and style is None:
        p.paragraph_format.first_line_indent = Cm(0.74)
    if text:
        r = p.add_run(text)
        set_run_font(r, 12)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    r = p.add_run(text)
    if level == 1:
        set_run_font(r, 16, bold=True, font_name="Heiti SC")
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(8)
    elif level == 2:
        set_run_font(r, 14, bold=True, font_name="Heiti SC")
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(6)
    else:
        set_run_font(r, 12.5, bold=True, font_name="Heiti SC")
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
    return p


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    set_run_font(r, 10.5, bold=bold)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_table(doc, rows, widths_cm):
    table = doc.add_table(rows=1, cols=len(widths_cm))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, w in enumerate(widths_cm):
        table.columns[i].width = Cm(w)
    header = table.rows[0].cells
    for i, text in enumerate(rows[0]):
        shade_cell(header[i], "F2F2F2")
        set_cell_text(header[i], text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for row in rows[1:]:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            set_cell_text(cells[i], text, align=WD_ALIGN_PARAGRAPH.LEFT if i else WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    return table


def build_doc():
    create_architecture_image()
    create_workflow_image()
    create_intent_image()

    doc = Document()
    sec = doc.sections[0]
    sec.start_type = WD_SECTION_START.NEW_PAGE
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = Inches(1.25)
    sec.right_margin = Inches(1.25)
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.footer_distance = Cm(1.0)

    styles = doc.styles
    styles["Normal"].font.name = "Times New Roman"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Songti SC")
    styles["Normal"].font.size = Pt(12)
    for style_name in ["Heading 1", "Heading 2", "Heading 3"]:
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Heiti SC")
        style.font.color.rgb = RGBColor(0, 0, 0)

    add_page_number(sec.footer.paragraphs[0])

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(26)
    title.paragraph_format.space_after = Pt(24)
    r = title.add_run("直播脚本生成智能体AI赋能解决方案")
    set_run_font(r, 18, bold=True, font_name="Heiti SC")

    add_heading(doc, "项目背景与目标", 1)
    add_paragraph(doc, "随着线上营销、直播带货和政企业务宣推场景的快速增长，直播脚本已经从简单的口播文案发展为承载产品卖点、用户互动、合规表达和转化引导的关键内容资产。传统脚本编写主要依赖运营人员经验，存在资料整理耗时长、卖点表达不稳定、转化节奏不统一、违禁词风险难以及时发现等问题，难以支撑多产品、多场景、高频次的直播运营需求。")
    add_paragraph(doc, "本项目以构建“资料解析—脚本生成—质量评估—订正优化”的直播脚本生成智能体为目标，深度融合 OpenAI 兼容大模型接口、对话上下文管理、用户长期记忆、违禁词实时过滤和流式输出能力，形成面向直播运营人员的一站式智能创作工具。系统能够根据商品信息、目标客群、直播场景和用户补充要求自动生成完整脚本，并通过评分与订正闭环提升脚本质量。")
    add_paragraph(doc, "通过本系统建设，可显著降低脚本初稿生产成本，提升脚本表达的一致性、专业性和合规性；同时沉淀用户偏好、历史对话和优秀话术，为后续直播内容复用、运营统计和精细化管理提供数据基础。")

    add_heading(doc, "系统架构", 1)
    add_paragraph(doc, "本系统采用“数据层—接入与解析层—AI智能中枢层—应用服务层—展示与运维层”的分层架构，后端基于 FastAPI 构建统一服务入口，前端基于 React 与 Vite 提供轻量化交互界面，数据库采用 MySQL 与 SQLAlchemy 进行业务数据持久化。整体架构既满足快速交付，又兼顾后续扩展、管理维护和多场景复用。")
    doc.add_picture(str(ARCH_IMG), width=Cm(15.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = add_paragraph(doc, "图1 直播脚本生成智能体架构图", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    cap.paragraph_format.space_after = Pt(10)
    add_paragraph(doc, "数据层负责承载系统运行所需的核心业务数据，包括商品资料、直播场景信息、对话消息、用户长期记忆、违禁词库、平台用户信息和统计日志等。系统通过结构化数据表记录管理员、对话、消息、用户记忆、违禁词和平台用户等实体，为脚本生成、历史追溯、用户画像和运营统计提供稳定的数据底座。")
    add_paragraph(doc, "接入与解析层面向用户上传文件和文本输入，支持 txt、docx、pdf、xlsx 等常见资料格式，对商品介绍、活动政策、卖点清单和历史脚本进行解析、清洗和要素抽取。该层将不同格式的资料统一整理为可被大模型理解的上下文片段，减少人工复制粘贴和格式整理成本。")
    add_paragraph(doc, "AI智能中枢层是系统核心能力所在，负责意图识别、上下文装配、大模型调用、三步脚本生成流程、评分订正、记忆保存与违禁词过滤。所有大模型调用均通过 OpenAI 兼容接口完成，可根据部署环境灵活切换模型、基础地址和调用参数。系统在流式响应过程中实时过滤违禁词，并将最近对话历史与长期记忆注入上下文，保证输出既连贯又符合用户偏好。")
    add_paragraph(doc, "应用服务层围绕直播脚本生产的关键工作流提供 RESTful API，包括主智能体接口、脚本生成、脚本打分、脚本订正、对话管理、统计分析、管理员认证、违禁词维护和用户记忆管理等。前端展示与运维层则提供普通用户创作界面和管理后台，支持 SSE 流式展示、历史对话查看、CSV 导出和 Docker 容器化部署。")

    add_heading(doc, "关键技术", 1)
    add_heading(doc, "3.1 智能体编排与上下文管理", 2)
    add_heading(doc, "3.1.1 对话历史与用户记忆构建", 3)
    add_paragraph(doc, "直播脚本生成不是一次性的文本补全任务，而是需要持续理解用户偏好、商品定位、直播风格和历史修改意见的创作过程。本系统在每次请求中自动加载最近 20 条对话消息，并结合用户长期记忆形成完整上下文，使大模型能够在连续沟通中保持一致的表达风格和业务理解。")
    add_paragraph(doc, "用户记忆服务用于保存明确要求记住的信息，例如常用开场风格、禁用表达、目标客群特征、品牌语气和特定直播间规则等。系统通过独立的记忆接口进行新增、查询、更新和删除，避免把偏好信息散落在临时对话中，从而提升跨会话复用能力。")
    rows = [
        ["功能模块", "功能描述"],
        ["对话历史加载", "按 dialog_id 自动读取最近 20 条用户与助手消息，构建连续上下文，减少重复说明。"],
        ["用户长期记忆", "保存用户明确要求记住的信息，并在后续生成时注入大模型上下文，提升个性化效果。"],
        ["平台用户识别", "记录地市、区县、工号、姓名和岗位等平台用户信息，支撑权限识别与运营统计。"],
        ["消息持久化", "对请求 ID、角色、内容和对话归属进行存储，便于历史追溯和管理分析。"],
        ["统计分析", "汇总对话次数、用户使用情况和筛选维度，并支持 CSV 导出。"],
    ]
    add_table(doc, rows, [4.2, 10.4])
    add_paragraph(doc, "表1 上下文与记忆核心功能", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "3.1.2 意图识别与工具路由", 3)
    add_paragraph(doc, "系统通过意图识别机制分析用户输入，将请求划分为生成直播脚本、脚本打分、脚本订正、脚本结构分析、保存记忆和普通对话等类型。不同意图会进入不同的处理链路，既保证主任务流程清晰，又避免所有请求都被简单处理为通用问答。")
    doc.add_picture(str(CLASSIFY_IMG), width=Cm(14.8))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_paragraph(doc, "图2 意图识别与工具路由机制", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    add_paragraph(doc, "当用户提出“帮我写直播脚本”“根据这个产品生成话术”等请求时，系统进入 generate_script 链路；当用户要求评价已有脚本时，进入 score_script 链路；当用户要求优化、改写或规避风险表达时，进入 revise_script 链路；当用户明确提出“记住我的偏好”时，进入 save_memory 链路。该路由方式使智能体能够以业务动作组织能力，而不是仅以自然语言回复组织能力。")

    add_heading(doc, "3.2 直播脚本生成闭环", 2)
    add_paragraph(doc, "直播脚本生成采用“生成—打分—订正”的三步闭环。第一步根据产品信息、用户要求、历史上下文和长期记忆生成完整脚本；第二步从吸引力、逻辑性、感染力、专业性等维度对脚本进行质量评估；第三步结合评分意见对脚本进行订正优化，形成更适合直播使用的最终版本。")
    doc.add_picture(str(FLOW_IMG), width=Cm(15.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_paragraph(doc, "图3 直播脚本生成三步闭环流程", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    rows = [
        ["流程环节", "核心处理", "输出结果"],
        ["脚本生成", "综合商品资料、目标客群、直播目标、用户偏好和上下文历史，生成包含开场、讲解、互动、促单、收尾的完整脚本。", "直播脚本初稿"],
        ["质量评估", "围绕吸引力、逻辑性、感染力、专业性进行评分，并指出表达亮点和可优化问题。", "评分结果与修改建议"],
        ["订正优化", "根据评估意见调整节奏、补强卖点、优化话术、规避违禁词和不合规表达。", "可直接使用的优化稿"],
        ["流式返回", "通过 SSE 逐步返回处理进度与生成内容，降低等待感并提升交互体验。", "实时可见的生成过程"],
    ]
    add_table(doc, rows, [3.0, 8.2, 3.4])
    add_paragraph(doc, "表2 脚本生成闭环关键步骤", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "3.3 违禁词过滤与安全可控输出", 2)
    add_paragraph(doc, "直播场景对表达合规性要求较高，涉及夸大宣传、绝对化用语、敏感词和平台限制词等风险。本系统内置违禁词管理能力，管理员可在后台维护违禁词及替换词，并支持 Excel 批量导入、更新、删除和清空。")
    add_paragraph(doc, "在智能体流式输出过程中，系统会对生成内容进行实时过滤，将命中的违禁词替换为配置的合规表达。与生成结束后再处理相比，流式过滤能够让用户看到的每一段输出都保持相对安全，减少二次编辑负担。该机制与模型提示词约束形成双重控制：提示词负责源头约束，违禁词服务负责结果兜底。")

    add_heading(doc, "3.4 文件解析与多格式资料接入", 2)
    add_paragraph(doc, "直播脚本创作常常依赖商品介绍、活动政策、历史脚本、Excel 卖点清单和 PDF 宣传材料。系统支持 txt、docx、pdf、xlsx 等文件上传，最大文件 10MB，通过解析服务将文件内容转化为统一文本上下文。")
    add_paragraph(doc, "对于 Word 与 PDF 文档，系统提取正文内容和关键段落；对于 Excel 文件，系统读取表格中的商品参数、卖点、价格、活动信息和注意事项；对于纯文本资料，系统进行清洗和分段。解析后的内容会与用户输入共同进入智能体上下文，为生成更贴近商品实际情况的脚本提供依据。")

    add_heading(doc, "部署方案", 1)
    add_heading(doc, "4.1 模型与接口选型", 2)
    add_paragraph(doc, "在模型调用方面，本项目采用 OpenAI SDK 与 OpenAI 兼容接口，默认模型可通过 OPENAI_MODEL 环境变量配置，默认基础地址可通过 OPENAI_BASE_URL 配置。该设计将业务系统与具体模型供应方解耦，使系统既可接入云端大模型服务，也可接入企业内部部署的兼容接口。")
    rows = [
        ["配置项", "说明", "默认值/建议"],
        ["OPENAI_API_KEY", "大模型接口访问密钥，用于鉴权和请求授权。", "由部署环境配置"],
        ["OPENAI_BASE_URL", "OpenAI 兼容接口地址，可指向云端或内网模型网关。", "http://host.docker.internal:8765/v1"],
        ["OPENAI_MODEL", "脚本生成、评分和订正所使用的模型名称。", "Deepseek-V4-Flash"],
        ["SECRET_KEY", "JWT 签名密钥，用于管理员与用户认证。", "生产环境固定配置"],
        ["MYSQL_DATABASE", "业务数据库名称，存储对话、记忆、违禁词和用户信息。", "living_stream_agent"],
    ]
    add_table(doc, rows, [3.6, 7.2, 3.8])
    add_paragraph(doc, "表3 核心环境变量与模型接口配置", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "4.2 后端与数据库部署", 2)
    add_paragraph(doc, "后端服务基于 Python 3.11 与 FastAPI 构建，提供统一的 /chat/api/ 接口前缀，并通过 SQLAlchemy 连接 MySQL 8.0。系统核心 API 包括智能体入口、对话管理、统计分析、管理员认证、违禁词管理、用户记忆和平台用户认证等。")
    add_paragraph(doc, "数据库通过 init_db.py 进行初始化，当前采用手动迁移方式管理表结构。主要数据模型包括 Admin、Dialog、DialogMessage、UserMemory、ForbiddenWord 和 PlatformUser，分别支撑管理员登录、对话存储、消息记录、用户长期记忆、违禁词过滤和平台用户身份信息。")
    add_paragraph(doc, "部署时可采用 Docker Compose 启动应用与 MySQL 服务，通过环境变量注入模型接口、数据库连接、JWT 密钥等配置。该方式能够降低本地环境差异影响，并便于后续迁移到政企云、专有云或容器平台。")

    add_heading(doc, "4.3 前端与交互体验", 2)
    add_paragraph(doc, "前端基于 React 19、Vite 6 和 React Router v7 构建，页面组件采用函数式组件与 Hooks，样式使用 CSS Modules 管理。用户可在前端发起脚本生成、评分、订正和普通对话请求，并通过流式响应实时查看生成过程。")
    add_paragraph(doc, "管理后台提供违禁词维护、管理员登录、密码修改和统计查看等能力，使运营人员能够在不修改代码的情况下维护敏感表达与替换规则。对话列表、消息详情和统计导出能力则为日常运营复盘提供数据支撑。")

    add_heading(doc, "4.4 API接口与业务能力", 2)
    add_paragraph(doc, "系统 API 统一采用 RESTful 风格，接口前缀为 /chat/api/，主智能体端点支持流式响应，响应格式为 JSON 或 text/event-stream。通过接口分层，前端页面、管理后台以及未来外部系统都可以复用同一套业务能力。")
    rows = [
        ["接口类别", "代表接口", "业务说明"],
        ["智能体接口", "POST /chat/api/agent", "统一智能体入口，负责意图识别、文件解析、上下文加载、大模型调用和流式输出。"],
        ["脚本处理接口", "generate / score / revise", "分别承载直播脚本生成、脚本评分和脚本订正能力，支撑三步闭环。"],
        ["对话管理接口", "dialogs / messages", "创建对话、查询对话列表、获取消息明细、删除对话并保存生成内容。"],
        ["统计与导出接口", "stats / export", "提供总览统计、用户统计、筛选条件和 CSV 导出能力，辅助运营分析。"],
        ["管理接口", "admin / forbidden-words / memories", "提供管理员登录、密码修改、违禁词维护和用户记忆维护能力。"],
    ]
    add_table(doc, rows, [3.2, 4.8, 6.6])
    add_paragraph(doc, "表4 主要API能力清单", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "4.5 数据模型与持久化设计", 2)
    add_paragraph(doc, "数据库设计围绕脚本生成业务闭环展开，既保存用户使用过程中的对话与消息，也保存影响生成质量的长期记忆和违禁词规则。对管理员、平台用户、对话、消息、记忆、违禁词等对象进行独立建模，能够保证业务边界清晰，并便于后续扩展权限、统计和审计能力。")
    rows = [
        ["数据模型", "核心字段", "作用说明"],
        ["Admin", "username、hashed_password、is_active", "支撑后台管理员登录、密码管理和账号启停。"],
        ["Dialog", "user_id、tool_id、title、request_count", "记录用户会话、工具来源和请求次数，用于历史管理与统计。"],
        ["DialogMessage", "dialog_id、request_id、role、content", "保存用户与助手消息，构成上下文回溯基础。"],
        ["UserMemory", "user_id、content、created_at、updated_at", "沉淀用户长期偏好和直播风格要求。"],
        ["ForbiddenWord", "word、replacement", "维护违禁词和替换词，实现流式输出合规兜底。"],
        ["PlatformUser", "platform_user_id、lan_name、staff_code", "保存平台用户身份与组织信息，支撑用户识别。"],
    ]
    add_table(doc, rows, [3.0, 5.2, 6.4])
    add_paragraph(doc, "表5 核心数据模型设计", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "4.6 运维策略与安全控制", 2)
    add_paragraph(doc, "系统通过环境变量管理模型密钥、数据库连接、JWT 密钥和模型名称等敏感配置，生产环境应使用固定 SECRET_KEY 并配置安全的数据库密码。管理员认证采用 JWT 机制，后台接口在访问前进行身份校验，降低未授权维护违禁词和统计数据的风险。")
    add_paragraph(doc, "运维层面可采用 Docker Compose 完成一体化部署，应用服务与 MySQL 数据库独立运行，日志通过容器日志进行查看和归档。针对大模型接口，应配置超时、异常捕获和错误提示机制，避免模型服务短暂不可用影响前端整体体验。")
    add_paragraph(doc, "在内容安全方面，系统形成“提示词约束 + 违禁词规则 + 人工复核”的三层控制。模型负责生成时尽量遵守表达规范，违禁词服务负责输出过程中的实时兜底，运营人员则可在正式直播前进行最后审核，确保脚本既高效生成又符合平台和业务要求。")

    add_heading(doc, "实施计划", 1)
    add_paragraph(doc, "项目实施可按照基础环境准备、核心功能联调、管理后台配置、试运行优化和正式上线五个阶段推进。每个阶段均围绕可交付能力展开，避免将模型能力、业务规则和前端交互割裂实施。")
    rows = [
        ["阶段", "主要工作", "交付成果"],
        ["环境准备", "配置 MySQL、后端依赖、前端依赖和 OpenAI 兼容接口参数。", "可运行的基础服务环境"],
        ["功能联调", "联调脚本生成、评分、订正、文件解析、对话保存和流式输出。", "可完成主流程的智能体服务"],
        ["规则配置", "导入违禁词、配置替换词、整理常用直播场景和用户记忆样例。", "可控的生成规则与记忆基础"],
        ["试运行优化", "选择典型商品和直播场景试用，收集脚本质量、响应速度和合规命中反馈。", "优化后的提示词和业务参数"],
        ["正式上线", "开放给运营人员使用，并建立日志巡检、数据备份和规则维护机制。", "稳定运行的直播脚本生成系统"],
    ]
    add_table(doc, rows, [2.8, 7.2, 4.6])
    add_paragraph(doc, "表6 项目实施计划", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)

    add_heading(doc, "应用价值", 1)
    add_paragraph(doc, "通过直播脚本生成智能体建设，运营人员可以将主要精力从重复撰写初稿转向商品策略、直播节奏和转化细节优化。系统以智能生成降低生产成本，以评分订正提升脚本质量，以违禁词过滤降低合规风险，以用户记忆和历史对话沉淀个性化创作资产。")
    add_paragraph(doc, "后续可进一步扩展行业话术模板、优秀脚本知识库、直播复盘数据接入、A/B 脚本效果分析和多平台合规词库，形成从脚本生成到直播效果反馈的完整运营闭环。")
    add_heading(doc, "5.1 预期成效", 2)
    add_paragraph(doc, "系统上线后，将在内容生产效率、脚本质量稳定性、合规风险控制和运营管理精细化方面形成直接价值。相比完全依赖人工编写的方式，智能体能够快速完成初稿生成，并通过评分订正机制持续提升脚本可用性。")
    rows = [
        ["成效维度", "建设前痛点", "建设后效果"],
        ["生产效率", "运营人员需要反复整理商品资料并手工组织脚本结构，初稿产出耗时较长。", "系统自动完成资料理解和脚本组织，快速形成可编辑初稿。"],
        ["质量稳定", "不同人员写作经验差异较大，脚本风格和转化节奏不统一。", "通过统一提示词、评分维度和订正流程，提升输出一致性。"],
        ["合规控制", "违禁词和平台限制表达主要依赖人工检查，存在漏检风险。", "违禁词库实时过滤并支持后台维护，降低不合规表达进入正式脚本的概率。"],
        ["知识沉淀", "历史脚本和用户偏好分散在聊天记录或本地文件中，难以复用。", "通过对话管理和长期记忆机制沉淀可复用创作资产。"],
        ["运营分析", "缺少统一使用统计，难以评估工具价值和高频用户需求。", "统计接口支持总览、用户维度和 CSV 导出，便于复盘优化。"],
    ]
    add_table(doc, rows, [3.0, 5.8, 5.8])
    add_paragraph(doc, "表7 项目预期成效", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    add_heading(doc, "5.2 结论", 2)
    add_paragraph(doc, "直播脚本生成智能体以现有 FastAPI、React、MySQL 与 OpenAI 兼容模型接口为基础，围绕直播脚本生产的真实流程构建可落地的智能化能力。系统既能够支撑用户快速生成脚本，也能够通过评分、订正、记忆和违禁词过滤形成闭环控制，具备较强的业务适配性和扩展空间。")
    add_paragraph(doc, "综合来看，本方案适合作为直播运营内容生产的基础智能体平台，后续可在行业知识库、脚本效果反馈、团队协同和多平台合规规则方面继续增强，逐步形成覆盖直播前策划、直播中执行和直播后复盘的智能运营体系。")

    doc.save(FINAL_DOCX)

    ARTIFACT_MD.write_text(
        "\n".join(
            [
                "# Template Distillation Notes",
                "",
                "Reference: 内审稽核智能体-技术方案.docx",
                "SHA-256: e4d4b31ca25bb18d63ff7e759b09eacb5ec3035a6cb0812c62c14675c4c3bb5b",
                "Page system: A4 portrait, one section, margins L/R 1.25in T/B 1.00in, centered footer page number.",
                "Typography: Chinese body follows 宋体 12pt with Times New Roman latin fallback; headings use 黑体-like hierarchy.",
                "Content flow: formal technical solution, sections include project background, system architecture, key technologies, deployment plan, with figures and tables.",
                "Fidelity approach: recreate the source-derived page system, heading ladder, dense explanatory prose, simple bordered tables, centered figure captions, and restrained black-and-white technical-plan style.",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_doc()
