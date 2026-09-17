# 1. Import libraries

import streamlit as st
import json
import random
import re
from google import genai

client = genai.Client()

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

def format_money(amount):
    return f"{amount / 1000000000:.2f} tỷ VNĐ"

# 3. AI helper functions

def ask_ai(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        print("AI RESPONSE:")
        print(response.text)
        return response.text
    except Exception as e:
        print("AI error:", e)
        return None

def get_json(text):
    if not text:
        return None

    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)

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
    available = [
        c for c in crises
        if c["id"] not in st.session_state.used_crises
    ]

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
Hãy đánh giá quyết định của người chơi dựa trên tình huống cụ thể dưới đây.

TÌNH HUỐNG:
{json.dumps(crisis, ensure_ascii=False)}

QUYẾT ĐỊNH CỦA NGƯỜI CHƠI:
{decision}

GIẢI THÍCH CỦA NGƯỜI CHƠI:
{reasoning}

Hãy chấm điểm từ 0 đến 10 cho 6 tiêu chí:
- decision_making
- risk_management
- customer_service
- financial_management
- reputation_management
- feasibility

Hãy nhận xét CỤ THỂ dựa trên chính tình huống và quyết định của người chơi.

Cần trả về:
- strengths: điểm mạnh cụ thể
- weaknesses: điểm hạn chế cụ thể
- feedback: lời khuyên cụ thể
- budget_change: thay đổi ngân sách
- satisfaction_change: thay đổi mức hài lòng của khách
- reputation_change: thay đổi danh tiếng

satisfaction_change phải nằm trong khoảng -15 đến 15.
reputation_change phải nằm trong khoảng -15 đến 15.

budget_change là số tiền thay đổi trong ngân sách GAME.
Ngân sách ban đầu của game là 10000.
Không sử dụng tiền thật hoặc đơn vị tiền thực tế lớn như hàng triệu, tỷ.
Với một hành động có chi phí lớn, hãy ước tính chi phí trong phạm vi ngân sách của game.

CHỈ TRẢ VỀ JSON HỢP LỆ.
KHÔNG viết markdown.
KHÔNG viết ```json.
KHÔNG giải thích bên ngoài JSON.

JSON phải có đúng dạng:

{{
    "decision_making": 0,
    "risk_management": 0,
    "customer_service": 0,
    "financial_management": 0,
    "reputation_management": 0,
    "feasibility": 0,
    "strengths": "Nhận xét cụ thể",
    "weaknesses": "Nhận xét cụ thể",
    "feedback": "Lời khuyên cụ thể",
    "satisfaction_change": 0,
    "reputation_change": 0
}}
"""

    result = ask_ai(prompt)
    data = get_json(result)

    if not data:
        print("AI không trả về JSON hợp lệ. Đang dùng dữ liệu mặc định.")

        data = {
            "decision_making": 6,
            "risk_management": 6,
            "customer_service": 6,
            "financial_management": 6,
            "reputation_management": 6,
            "feasibility": 6,
            "strengths": "Không thể đọc kết quả đánh giá từ AI.",
            "weaknesses": "AI không trả về dữ liệu đúng định dạng.",
            "feedback": "Kiểm tra phản hồi của AI trong Terminal.",
            "budget_change": 0,
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
        data["satisfaction_change"] = float(
            data.get("satisfaction_change", 0)
        )
    except:
        data["satisfaction_change"] = 0

    try:
        data["reputation_change"] = float(
            data.get("reputation_change", 0)
        )
    except:
        data["reputation_change"] = 0

    data["satisfaction_change"] = max(
        -15, min(15, data["satisfaction_change"])
    )

    data["reputation_change"] = max(
        -15, min(15, data["reputation_change"])
    )

    return data

# 6. Final report

def generate_final_report():
    history_text = json.dumps(
        state["history"],
        ensure_ascii=False,
        indent=2
    )

    rounds_played = len(state["history"])

    prompt = f"""
Bạn là chuyên gia đào tạo quản lý du lịch.

Người chơi đã hoàn thành {rounds_played} vòng mô phỏng khủng hoảng du lịch.

KẾT QUẢ HIỆN TẠI:
- Mức hài lòng khách hàng: {state["satisfaction"]}/100
- Danh tiếng điểm đến: {state["reputation"]}/100

LỊCH SỬ CÁC VÒNG ĐÃ CHƠI:
{history_text}

Hãy phân tích quá trình ra quyết định của người chơi dựa trên tất cả các vòng đã chơi.

QUY TẮC PHÂN LOẠI:
- Từ 70 đến 100: "Cao"
- Từ 40 đến dưới 70: "Trung bình"
- Dưới 40: "Thấp"

Hãy đánh giá:
- satisfaction_level
- reputation_level

Sau đó giải thích cụ thể vì sao hai chỉ số hiện tại đạt mức đó.

Phân tích phải dựa trên:
- quyết định của người chơi
- lý do của người chơi
- điểm số
- feedback
- thay đổi mức hài lòng
- thay đổi danh tiếng

Hãy xác định:
- strengths: những điểm mạnh trong tư duy quản lý
- weaknesses: những điểm cần cải thiện
- lessons: đúng 3 bài học quan trọng
- management_advice: lời khuyên cụ thể để cải thiện khả năng quản lý khủng hoảng du lịch

Không chỉ nhìn vào điểm số.
Hãy tìm những xu hướng lặp lại trong cách người chơi ra quyết định.

Nếu người chơi mới chỉ hoàn thành 1 vòng hoặc một vài vòng,
hãy phân tích dựa trên dữ liệu hiện có và không giả định những vòng chưa chơi.

CHỈ TRẢ VỀ JSON HỢP LỆ.

KHÔNG viết markdown.
KHÔNG viết ```json.
KHÔNG giải thích bên ngoài JSON.

JSON phải có đúng dạng:

{{
    "satisfaction_level": "Cao",
    "satisfaction_analysis": "Giải thích cụ thể dựa trên các vòng đã chơi",
    "reputation_level": "Thấp",
    "reputation_analysis": "Giải thích cụ thể dựa trên các vòng đã chơi",
    "strengths": "Điểm mạnh cụ thể",
    "weaknesses": "Điểm cần cải thiện cụ thể",
    "lessons": [
        "Bài học 1",
        "Bài học 2",
        "Bài học 3"
    ],
    "management_advice": "Lời khuyên cụ thể"
}}
"""

    result = ask_ai(prompt)

    print("FINAL REPORT RESPONSE:")
    print(result)

    data = get_json(result)

    if not data:
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

        return {
            "satisfaction_level": satisfaction_level,
            "satisfaction_analysis": (
                f"Mức hài lòng hiện tại là "
                f"{state['satisfaction']:.0f}/100."
            ),
            "reputation_level": reputation_level,
            "reputation_analysis": (
                f"Danh tiếng hiện tại là "
                f"{state['reputation']:.0f}/100."
            ),
            "strengths": "Chưa thể tạo phân tích từ AI.",
            "weaknesses": "Chưa thể tạo phân tích từ AI.",
            "lessons": [
                "Cần cân bằng giữa khách hàng và hoạt động kinh doanh.",
                "Cần đánh giá rủi ro trước khi đưa ra quyết định.",
                "Cần xem xét tác động dài hạn của mỗi quyết định."
            ],
            "management_advice": (
                "Hãy tiếp tục luyện tập khả năng phân tích tình huống, "
                "quản lý rủi ro và cân đối nguồn lực."
            )
        }

    if data.get("satisfaction_level") not in [
        "Cao",
        "Trung bình",
        "Thấp"
    ]:
        if state["satisfaction"] >= 70:
            data["satisfaction_level"] = "Cao"
        elif state["satisfaction"] >= 40:
            data["satisfaction_level"] = "Trung bình"
        else:
            data["satisfaction_level"] = "Thấp"

    if data.get("reputation_level") not in [
        "Cao",
        "Trung bình",
        "Thấp"
    ]:
        if state["reputation"] >= 70:
            data["reputation_level"] = "Cao"
        elif state["reputation"] >= 40:
            data["reputation_level"] = "Trung bình"
        else:
            data["reputation_level"] = "Thấp"

    if not isinstance(data.get("lessons"), list):
        data["lessons"] = []

    while len(data["lessons"]) < 3:
        data["lessons"].append(
            "Tiếp tục luyện tập khả năng ra quyết định trong khủng hoảng."
        )

    data["lessons"] = data["lessons"][:3]

    return data

def show_final_page():
    rounds_played = len(state["history"])

    st.title(
        f"BÁO CÁO SAU {rounds_played} VÒNG"
    )

    report = st.session_state.final_report

    st.subheader("TỔNG QUAN")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Hài lòng khách hàng",
            f"{state['satisfaction']:.0f}/100"
        )

        st.write(
            f"**Mức độ: {report['satisfaction_level']}**"
        )

    with col2:
        st.metric(
            "Danh tiếng điểm đến",
            f"{state['reputation']:.0f}/100"
        )

        st.write(
            f"**Mức độ: {report['reputation_level']}**"
        )

    st.subheader("PHÂN TÍCH MỨC HÀI LÒNG")

    st.write(
        report["satisfaction_analysis"]
    )

    st.subheader("PHÂN TÍCH DANH TIẾNG")

    st.write(
        report["reputation_analysis"]
    )

    st.subheader("ĐIỂM MẠNH")

    st.success(
        report["strengths"]
    )

    st.subheader("ĐIỂM CẦN CẢI THIỆN")

    st.warning(
        report["weaknesses"]
    )

    st.subheader("3 BÀI HỌC")

    for i, lesson in enumerate(report["lessons"], 1):
        st.write(
            f"**{i}.** {lesson}"
        )

    st.subheader("LỜI KHUYÊN VỀ QUẢN LÝ DU LỊCH")

    st.info(
        report["management_advice"]
    )

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

    decision = st.session_state[
        f"decision_{round_number}"
    ].strip()

    reasoning = st.session_state[
        f"reasoning_{round_number}"
    ].strip()

    if not decision or not reasoning:
        st.warning("Vui lòng nhập quyết định và lý do.")
        return

    result = evaluate_decision(
        decision,
        reasoning
    )

    state["satisfaction"] += (
        result["satisfaction_change"]
    )

    state["reputation"] += (
        result["reputation_change"]
    )

    state["satisfaction"] = max(
        0,
        min(100, state["satisfaction"])
    )

    state["reputation"] = max(
        0,
        min(100, state["reputation"])
    )

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

st.write(
    f"### {crisis['title']}"
)

st.write(
    f"**Loại:** {crisis['type']}"
)

st.write(
    f"**Mức độ:** {crisis['severity']}/10"
)

st.write(
    f"**Số khách bị ảnh hưởng:** "
    f"{crisis['affected_tourists']}"
)

st.write(
    crisis["description"]
)

st.subheader("QUYẾT ĐỊNH CỦA BẠN")

round_number = state["round"]

st.text_input(
    "Quyết định của bạn",
    key=f"decision_{round_number}"
)

st.text_area(
    "Giải thích",
    key=f"reasoning_{round_number}"
)

if not st.session_state.answered:
    if st.button("ĐÁNH GIÁ QUYẾT ĐỊNH"):
        evaluate()
        st.rerun()

# Chỉ hiển thị kết quả nếu kết quả thuộc đúng vòng hiện tại

if (
    st.session_state.result is not None
    and st.session_state.result_round == state["round"]
):

    st.subheader("KẾT QUẢ")

    result = st.session_state.result

    st.write(
        f"### ĐIỂM TỔNG: {result['total']}/100"
    )

    st.write(
        f"Ra quyết định: "
        f"{result['decision_making']:.1f}/10"
    )

    st.write(
        f"Quản lý rủi ro: "
        f"{result['risk_management']:.1f}/10"
    )

    st.write(
        f"Chăm sóc khách hàng: "
        f"{result['customer_service']:.1f}/10"
    )

    st.write(
        f"Quản lý tài chính: "
        f"{result['financial_management']:.1f}/10"
    )

    st.write(
        f"Quản lý danh tiếng: "
        f"{result['reputation_management']:.1f}/10"
    )

    st.write(
        f"Tính khả thi: "
        f"{result['feasibility']:.1f}/10"
    )

    st.write("**Ưu điểm:**")

    st.success(
        result["strengths"]
    )

    st.write("**Điểm hạn chế:**")

    st.warning(
        result["weaknesses"]
    )

    st.write("**Nhận xét:**")

    st.info(
        result["feedback"]
    )

    st.write(
        f"**Mức hài lòng:** "
        f"{result['satisfaction_change']:+.0f}"
    )

    st.write(
        f"**Danh tiếng:** "
        f"{result['reputation_change']:+.0f}"
    )

    st.divider()

    if st.button("XEM BÁO CÁO HIỆN TẠI"):
        st.session_state.final_report = (
            generate_final_report()
        )

        st.session_state.page = "final"

        st.rerun()

    if state["round"] < 5:

        if st.button("VÒNG TIẾP THEO"):
            next_round()
            st.rerun()

    else:

        st.success("HOÀN THÀNH 5 VÒNG")

        st.write(
            f"**Mức hài lòng cuối:** "
            f"{state['satisfaction']:.0f}/100"
        )

        st.write(
            f"**Danh tiếng cuối:** "
            f"{state['reputation']:.0f}/100"
        )

        if st.button("XEM BÁO CÁO TỔNG KẾT"):
            st.session_state.final_report = (
                generate_final_report()
            )

            st.session_state.page = "final"

            st.rerun()