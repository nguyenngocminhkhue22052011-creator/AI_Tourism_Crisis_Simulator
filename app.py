# 1. Import libraries

import streamlit as st
import json
import random
import re
from google import genai
from google.genai import types

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Tên model Gemini hợp lệ (đã sửa từ "gemini-3.6-flash" - model không tồn tại)
MODEL_NAME = "gemini-3.5-flash"

weights = {
    "decision_making": 0.25,
    "risk_management": 0.20,
    "customer_service": 0.20,
    "financial_management": 0.15,
    "reputation_management": 0.10,
    "feasibility": 0.10
}

# 2. Game state

if "state" not in st.session_state:
    st.session_state.state = {
        "round": 1,
        "satisfaction": 50,
        "reputation": 50,
        "history": []
    }

state = st.session_state.state

with open("crises.json", "r", encoding="utf-8") as f:
    crises = json.load(f)

if "used_crises" not in st.session_state:
    st.session_state.used_crises = set()

if "crisis" not in st.session_state:
    st.session_state.crisis = None

if "answered" not in st.session_state:
    st.session_state.answered = False

if "result" not in st.session_state:
    st.session_state.result = None

if "result_round" not in st.session_state:
    st.session_state.result_round = None

if "page" not in st.session_state:
    st.session_state.page = "game"

if "final_report" not in st.session_state:
    st.session_state.final_report = None

if "last_ai_error" not in st.session_state:
    st.session_state.last_ai_error = None


# 3. AI helper functions

def ask_ai(prompt, schema=None, retries=3):
    st.session_state.last_ai_error = None

    for attempt in range(retries):
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )

            if schema:
                config.response_schema = schema

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )

            text = response.text

            if text and text.strip():
                print(f"AI RESPONSE - lần {attempt + 1}:")
                print(text)
                return text

            print(f"AI trả về rỗng - lần {attempt + 1}")
            st.session_state.last_ai_error = "AI trả về nội dung rỗng."

        except Exception as e:
            print(f"AI error - lần {attempt + 1}: {e}")
            st.session_state.last_ai_error = str(e)

    return None


def get_json(text):
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)

        if not match:
            print("AI không trả về JSON:", text)
            return None

        try:
            return json.loads(match.group())

        except json.JSONDecodeError:
            print("JSON AI trả về không hợp lệ:", text)
            return None


# 4. Create crisis

def create_crisis():
    available = [c for c in crises if c["id"] not in st.session_state.used_crises]

    if not available:
        st.session_state.used_crises.clear()
        available = crises

    crisis = random.choice(available)
    st.session_state.used_crises.add(crisis["id"])

    return crisis


# 5. Evaluate decision

def evaluate_decision(decision, reasoning):

    crisis = st.session_state.crisis

    prompt = f"""
Bạn là chuyên gia quản lý khủng hoảng du lịch.

Hãy đánh giá quyết định của người chơi dựa trên tình huống cụ thể.

TÌNH HUỐNG:
{json.dumps(crisis, ensure_ascii=False)}

QUYẾT ĐỊNH:
{decision}

GIẢI THÍCH:
{reasoning}

Hãy chấm điểm từ 0 đến 10 cho:
- decision_making
- risk_management
- customer_service
- financial_management
- reputation_management
- feasibility

Hãy nhận xét cụ thể dựa trên tình huống và quyết định của người chơi.

Hãy xác định:
- strengths: điểm mạnh cụ thể
- weaknesses: điểm hạn chế cụ thể
- feedback: lời khuyên cụ thể
- satisfaction_change: thay đổi mức hài lòng của khách
- reputation_change: thay đổi danh tiếng

satisfaction_change phải từ -15 đến 15.
reputation_change phải từ -15 đến 15.

CHỈ trả về JSON hợp lệ.
Không thêm Markdown.
Không thêm ```json.
Không giải thích bên ngoài JSON.

Cấu trúc JSON bắt buộc:

{{
    "decision_making": 0,
    "risk_management": 0,
    "customer_service": 0,
    "financial_management": 0,
    "reputation_management": 0,
    "feasibility": 0,
    "strengths": "",
    "weaknesses": "",
    "feedback": "",
    "satisfaction_change": 0,
    "reputation_change": 0
}}
"""

    evaluation_schema = {
        "type": "object",
        "properties": {
            "decision_making": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "risk_management": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "customer_service": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "financial_management": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "reputation_management": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "feasibility": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
            },
            "strengths": {
                "type": "string"
            },
            "weaknesses": {
                "type": "string"
            },
            "feedback": {
                "type": "string"
            },
            "satisfaction_change": {
                "type": "number",
                "minimum": -15,
                "maximum": 15
            },
            "reputation_change": {
                "type": "number",
                "minimum": -15,
                "maximum": 15
            }
        },
        "required": [
            "decision_making",
            "risk_management",
            "customer_service",
            "financial_management",
            "reputation_management",
            "feasibility",
            "strengths",
            "weaknesses",
            "feedback",
            "satisfaction_change",
            "reputation_change"
        ],
        "propertyOrdering": [
            "decision_making",
            "risk_management",
            "customer_service",
            "financial_management",
            "reputation_management",
            "feasibility",
            "strengths",
            "weaknesses",
            "feedback",
            "satisfaction_change",
            "reputation_change"
        ]
    }

    required_keys = [
        "decision_making",
        "risk_management",
        "customer_service",
        "financial_management",
        "reputation_management",
        "feasibility",
        "strengths",
        "weaknesses",
        "feedback",
        "satisfaction_change",
        "reputation_change"
    ]

    data = None
    used_fallback = False

    for attempt in range(3):
        result = ask_ai(prompt, evaluation_schema, retries=1)
        data = get_json(result)

        if data and all(key in data for key in required_keys):
            break

        print(f"AI trả về dữ liệu không hợp lệ. Đang thử lại {attempt + 1}/3.")
        data = None

    if not data:
        used_fallback = True
        print("AI không trả về kết quả hợp lệ. Đang sử dụng dữ liệu mặc định.")

        data = {
            "decision_making": 6,
            "risk_management": 6,
            "customer_service": 6,
            "financial_management": 6,
            "reputation_management": 6,
            "feasibility": 6,
            "strengths": "Không thể đọc kết quả đánh giá từ AI.",
            "weaknesses": "AI không trả về dữ liệu đầy đủ.",
            "feedback": "Vui lòng thử lại.",
            "satisfaction_change": 0,
            "reputation_change": 0
        }

    total = 0

    for key in weights:
        try:
            data[key] = float(data.get(key, 5))
        except:
            data[key] = 5

        data[key] = max(0, min(10, data[key]))
        total += data[key] * weights[key]

    data["total"] = round(total * 10, 1)

    try:
        data["satisfaction_change"] = float(data.get("satisfaction_change", 0))
    except:
        data["satisfaction_change"] = 0

    try:
        data["reputation_change"] = float(data.get("reputation_change", 0))
    except:
        data["reputation_change"] = 0

    data["satisfaction_change"] = max(-15, min(15, data["satisfaction_change"]))
    data["reputation_change"] = max(-15, min(15, data["reputation_change"]))

    data["_used_fallback"] = used_fallback

    return data


# 6. Final report

def generate_final_report():

    history_text = json.dumps(state["history"], ensure_ascii=False, indent=2)
    rounds_played = len(state["history"])

    prompt = f"""
Bạn là chuyên gia đào tạo quản lý du lịch.

Người chơi đã hoàn thành {rounds_played} vòng mô phỏng khủng hoảng du lịch.

KẾT QUẢ HIỆN TẠI:

Mức hài lòng khách hàng:
{state["satisfaction"]}/100

Danh tiếng điểm đến:
{state["reputation"]}/100

LỊCH SỬ CÁC VÒNG:

{history_text}

Hãy phân tích quá trình ra quyết định của người chơi dựa trên dữ liệu đã có.

QUY TẮC:

Từ 70 đến 100: Cao
Từ 40 đến dưới 70: Trung bình
Dưới 40: Thấp

Hãy đánh giá:
- satisfaction_level
- reputation_level

Sau đó giải thích cụ thể vì sao hai chỉ số hiện tại đạt mức đó.

Phân tích dựa trên:
- quyết định
- lý do
- điểm số
- feedback
- thay đổi mức hài lòng
- thay đổi danh tiếng

Hãy xác định:
- strengths
- weaknesses
- lessons: đúng 3 bài học
- management_advice

Không chỉ nhìn vào điểm số.

Hãy tìm những xu hướng lặp lại trong cách người chơi ra quyết định.

Nếu người chơi mới chỉ hoàn thành một vài vòng, hãy chỉ phân tích dựa trên dữ liệu hiện có.

Hãy viết ngắn gọn nhưng cụ thể.

CHỈ trả về JSON hợp lệ.
Không thêm Markdown.
Không thêm ```json.
Không giải thích bên ngoài JSON.

Cấu trúc JSON bắt buộc:

{{
    "satisfaction_level": "",
    "satisfaction_analysis": "",
    "reputation_level": "",
    "reputation_analysis": "",
    "strengths": "",
    "weaknesses": "",
    "lessons": [],
    "management_advice": ""
}}
"""

    report_schema = {
        "type": "object",
        "properties": {
            "satisfaction_level": {
                "type": "string"
            },
            "satisfaction_analysis": {
                "type": "string"
            },
            "reputation_level": {
                "type": "string"
            },
            "reputation_analysis": {
                "type": "string"
            },
            "strengths": {
                "type": "string"
            },
            "weaknesses": {
                "type": "string"
            },
            "lessons": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "management_advice": {
                "type": "string"
            }
        },
        "required": [
            "satisfaction_level",
            "satisfaction_analysis",
            "reputation_level",
            "reputation_analysis",
            "strengths",
            "weaknesses",
            "lessons",
            "management_advice"
        ],
        "propertyOrdering": [
            "satisfaction_level",
            "satisfaction_analysis",
            "reputation_level",
            "reputation_analysis",
            "strengths",
            "weaknesses",
            "lessons",
            "management_advice"
        ]
    }

    required_keys = [
        "satisfaction_level",
        "satisfaction_analysis",
        "reputation_level",
        "reputation_analysis",
        "strengths",
        "weaknesses",
        "lessons",
        "management_advice"
    ]

    data = None
    used_fallback = False

    for attempt in range(3):
        result = ask_ai(prompt, report_schema, retries=1)

        print("FINAL REPORT RESPONSE:")
        print(result)

        data = get_json(result)

        if data and all(key in data for key in required_keys):
            break

        print(f"Báo cáo cuối không hợp lệ. Đang thử lại lần {attempt + 1}/3.")
        data = None

    if not data:
        used_fallback = True
        print("AI không trả về báo cáo cuối hợp lệ.")

        if state["satisfaction"] >= 70:
            satisfaction_level = "Cao"
        elif state["satisfaction"] >= 40:
            satisfaction_level = "Trung bình"
        else:
            satisfaction_level = "Thấp"

        if state["reputation"] >= 70:
            reputation_level = "Cao"
        elif state["reputation"] >= 40:
            reputation_level = "Trung bình"
        else:
            reputation_level = "Thấp"

        data = {
            "satisfaction_level": satisfaction_level,
            "satisfaction_analysis": f"Mức hài lòng hiện tại là {state['satisfaction']:.0f}/100.",
            "reputation_level": reputation_level,
            "reputation_analysis": f"Danh tiếng hiện tại là {state['reputation']:.0f}/100.",
            "strengths": "Chưa thể tạo phân tích từ AI.",
            "weaknesses": "Chưa thể tạo phân tích từ AI.",
            "lessons": [
                "Cần cân bằng giữa khách hàng và hoạt động kinh doanh.",
                "Cần đánh giá rủi ro trước khi đưa ra quyết định.",
                "Cần xem xét tác động dài hạn của mỗi quyết định."
            ],
            "management_advice": "Hãy tiếp tục luyện tập khả năng phân tích tình huống, quản lý rủi ro và cân đối nguồn lực."
        }

    if data.get("satisfaction_level") not in ["Cao", "Trung bình", "Thấp"]:
        if state["satisfaction"] >= 70:
            data["satisfaction_level"] = "Cao"
        elif state["satisfaction"] >= 40:
            data["satisfaction_level"] = "Trung bình"
        else:
            data["satisfaction_level"] = "Thấp"

    if data.get("reputation_level") not in ["Cao", "Trung bình", "Thấp"]:
        if state["reputation"] >= 70:
            data["reputation_level"] = "Cao"
        elif state["reputation"] >= 40:
            data["reputation_level"] = "Trung bình"
        else:
            data["reputation_level"] = "Thấp"

    if not isinstance(data.get("lessons"), list):
        data["lessons"] = []

    while len(data["lessons"]) < 3:
        data["lessons"].append("Tiếp tục luyện tập khả năng ra quyết định trong khủng hoảng.")

    data["lessons"] = data["lessons"][:3]

    data["_used_fallback"] = used_fallback

    return data


def show_final_page():

    rounds_played = len(state["history"])

    st.title(f"BÁO CÁO SAU {rounds_played} VÒNG")

    report = st.session_state.final_report

    if report.get("_used_fallback"):
        st.warning(
            "AI không phản hồi hợp lệ, báo cáo này đang dùng dữ liệu dự phòng "
            "(không phải phân tích thật từ AI). Kiểm tra log console để biết lỗi cụ thể."
        )
        if st.session_state.last_ai_error:
            with st.expander("Chi tiết lỗi AI"):
                st.code(st.session_state.last_ai_error)

    st.subheader("TỔNG QUAN")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Hài lòng khách hàng", f"{state['satisfaction']:.0f}/100")
        st.write(f"**Mức độ: {report['satisfaction_level']}**")

    with col2:
        st.metric("Danh tiếng điểm đến", f"{state['reputation']:.0f}/100")
        st.write(f"**Mức độ: {report['reputation_level']}**")

    st.subheader("PHÂN TÍCH MỨC HÀI LÒNG")
    st.write(report["satisfaction_analysis"])

    st.subheader("PHÂN TÍCH DANH TIẾNG")
    st.write(report["reputation_analysis"])

    st.subheader("ĐIỂM MẠNH")
    st.success(report["strengths"])

    st.subheader("ĐIỂM CẦN CẢI THIỆN")
    st.warning(report["weaknesses"])

    st.subheader("3 BÀI HỌC")

    for i, lesson in enumerate(report["lessons"], 1):
        st.write(f"**{i}.** {lesson}")

    st.subheader("LỜI KHUYÊN VỀ QUẢN LÝ DU LỊCH")
    st.info(report["management_advice"])

    if rounds_played < 5:
        if st.button("QUAY LẠI CHƠI TIẾP"):
            st.session_state.page = "game"
            st.rerun()


# 7. Game logic

def update_status():
    st.write(
        f"**Vòng {state['round']}/5** | "
        f"Hài lòng: {state['satisfaction']:.0f}/100 | "
        f"Danh tiếng: {state['reputation']:.0f}/100"
    )


def show_crisis():
    st.session_state.crisis = create_crisis()
    st.session_state.answered = False
    st.session_state.result = None
    st.session_state.result_round = None


def evaluate():

    if st.session_state.answered:
        return

    round_number = state["round"]

    decision = st.session_state[f"decision_{round_number}"].strip()
    reasoning = st.session_state[f"reasoning_{round_number}"].strip()

    if not decision or not reasoning:
        st.warning("Vui lòng nhập quyết định và lý do.")
        return

    with st.spinner("Đang đánh giá quyết định..."):
        result = evaluate_decision(decision, reasoning)

    state["satisfaction"] += result["satisfaction_change"]
    state["reputation"] += result["reputation_change"]

    state["satisfaction"] = max(0, min(100, state["satisfaction"]))
    state["reputation"] = max(0, min(100, state["reputation"]))

    state["history"].append({
        "round": state["round"],
        "crisis": st.session_state.crisis["title"],
        "decision": decision,
        "reasoning": reasoning,
        "score": result["total"],
        "decision_making": result["decision_making"],
        "risk_management": result["risk_management"],
        "customer_service": result["customer_service"],
        "financial_management": result["financial_management"],
        "reputation_management": result["reputation_management"],
        "feasibility": result["feasibility"],
        "satisfaction_change": result["satisfaction_change"],
        "reputation_change": result["reputation_change"],
        "feedback": result["feedback"]
    })

    st.session_state.result = result
    st.session_state.result_round = state["round"]
    st.session_state.answered = True


def next_round():

    if state["round"] >= 5:
        return

    state["round"] += 1

    st.session_state.crisis = create_crisis()
    st.session_state.answered = False
    st.session_state.result = None
    st.session_state.result_round = None


# 8. Page control

if st.session_state.page == "final":
    show_final_page()
    st.stop()


# 9. GUI

st.title("MÔ PHỎNG KHỦNG HOẢNG DU LỊCH")

if st.session_state.crisis is None:
    show_crisis()

update_status()

st.subheader("TÌNH HUỐNG")

crisis = st.session_state.crisis

st.write(f"### {crisis['title']}")
st.write(f"**Loại:** {crisis['type']}")
st.write(f"**Mức độ:** {crisis['severity']}/10")
st.write(f"**Số khách bị ảnh hưởng:** {crisis['affected_tourists']}")
st.write(crisis["description"])

st.subheader("QUYẾT ĐỊNH CỦA BẠN")

round_number = state["round"]

st.text_input("Quyết định của bạn", key=f"decision_{round_number}")
st.text_area("Giải thích", key=f"reasoning_{round_number}")

if not st.session_state.answered:
    if st.button("ĐÁNH GIÁ QUYẾT ĐỊNH"):
        evaluate()

if st.session_state.result is not None and st.session_state.result_round == state["round"]:

    st.subheader("KẾT QUẢ")

    result = st.session_state.result

    if result.get("_used_fallback"):
        st.warning(
            "AI không phản hồi hợp lệ, điểm và nhận xét dưới đây là dữ liệu dự phòng "
            "(không phải đánh giá thật từ AI)."
        )
        if st.session_state.last_ai_error:
            with st.expander("Chi tiết lỗi AI"):
                st.code(st.session_state.last_ai_error)

    st.write(f"### ĐIỂM TỔNG: {result['total']}/100")
    st.write(f"Ra quyết định: {result['decision_making']:.1f}/10")
    st.write(f"Quản lý rủi ro: {result['risk_management']:.1f}/10")
    st.write(f"Chăm sóc khách hàng: {result['customer_service']:.1f}/10")
    st.write(f"Quản lý tài chính: {result['financial_management']:.1f}/10")
    st.write(f"Quản lý danh tiếng: {result['reputation_management']:.1f}/10")
    st.write(f"Tính khả thi: {result['feasibility']:.1f}/10")

    st.write("**Ưu điểm:**")
    st.success(result["strengths"])

    st.write("**Điểm hạn chế:**")
    st.warning(result["weaknesses"])

    st.write("**Nhận xét:**")
    st.info(result["feedback"])

    st.write(f"**Mức hài lòng:** {result['satisfaction_change']:+.0f}")
    st.write(f"**Danh tiếng:** {result['reputation_change']:+.0f}")

    st.divider()

    if st.button("XEM BÁO CÁO HIỆN TẠI"):
        with st.spinner("Đang tạo báo cáo..."):
            st.session_state.final_report = generate_final_report()
        st.session_state.page = "final"
        st.rerun()

    if state["round"] < 5:

        if st.button("VÒNG TIẾP THEO"):
            next_round()
            st.rerun()

    else:

        st.success("HOÀN THÀNH 5 VÒNG")

        st.write(f"**Mức hài lòng cuối:** {state['satisfaction']:.0f}/100")
        st.write(f"**Danh tiếng cuối:** {state['reputation']:.0f}/100")

        if st.button("XEM BÁO CÁO TỔNG KẾT"):
            with st.spinner("Đang tạo báo cáo..."):
                st.session_state.final_report = generate_final_report()
            st.session_state.page = "final"
            st.rerun()
