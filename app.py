import streamlit as st
import re
import random
import time

def load_questions(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = []
    question_blocks = re.findall(r"(QUESTION \d+.*?Correct Answer: [A-Z]+(?:[A-Z])?)", content, re.DOTALL | re.IGNORECASE)

    for block in question_blocks:
        question_number_match = re.search(r"QUESTION (\d+)", block)
        question_number = int(question_number_match.group(1)) if question_number_match else 0

        correct_answer_match = re.search(r"Correct Answer: ([A-Z]+(?:[A-Z])?)", block, re.IGNORECASE)
        correct_answer = correct_answer_match.group(1).strip().upper() if correct_answer_match else ""

        # Remove "Correct Answer" line from the block
        temp_block = re.sub(r"Correct Answer: [A-Z]+(?:[A-Z])?", "", block, flags=re.IGNORECASE).strip()
        
        # Remove "QUESTION N" from the block
        temp_block_without_q_num = re.sub(r"QUESTION \d+\s*", "", temp_block, flags=re.IGNORECASE).strip()

        final_question_text = ""
        options = []

        # Find the split point between question text and options
        # This will look for the first occurrence of a line starting with an option letter (A., B., etc.)
        split_point_match = re.search(r"^[A-Z]\.", temp_block_without_q_num, re.MULTILINE)
        
        if split_point_match:
            # Everything before the first option marker is the question text
            final_question_text = temp_block_without_q_num[:split_point_match.start()].strip()
            options_text_part = temp_block_without_q_num[split_point_match.start():].strip()
            
            # Insert a temporary unique delimiter before each option start (e.g., "^[A-Z].")
            # This will allow us to split and keep the option marker with its text.
            temp_options_string = re.sub(r"(^[A-Z]\.)", r"####OPTION_DELIMITER####\1", options_text_part, flags=re.MULTILINE)
            
            # Split by the unique delimiter. The first element will often be empty or residual.
            options_raw_split = temp_options_string.split("####OPTION_DELIMITER####")
            
            # Filter out empty strings and strip whitespace from each option
            options = [opt.strip() for opt in options_raw_split if opt.strip()]
            
        else:
            # If no options (A., B., etc.) are found, the entire cleaned block is the question.
            final_question_text = temp_block_without_q_num
            options = []
            
        questions.append({
            "number": question_number,
            "text": final_question_text,
            "options": options,
            "answer": correct_answer
        })
    return questions

def mock_exam_page():
    st.header("모의고사 시험")

    # Create a placeholder for the timer in the main content area
    timer_placeholder = st.empty()

    total_time_seconds = 130 * 60 # 130 minutes
    
    # Initialize start_time if not set (first run of mock exam)
    if "start_time" not in st.session_state or st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    elapsed_seconds = int(time.time() - st.session_state.start_time)
    remaining_seconds = max(0, total_time_seconds - elapsed_seconds)

    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    timer_text = f"**남은 시간: {minutes:02d}:{seconds:02d}**"
    timer_placeholder.markdown(timer_text) # Display timer in the main content area

    if remaining_seconds == 0:
        st.warning("시간이 초과되었습니다! 시험이 자동 종료됩니다.")
        st.session_state.page = "grading_page"
        st.query_params["page"] = "grading_page" # Update URL
        st.rerun()
        return

    # Display current question
    current_q_index = st.session_state.current_question_index
    current_question = st.session_state.selected_questions[current_q_index]

    st.subheader(f"문제 {current_q_index + 1} / {len(st.session_state.selected_questions)}")
    st.markdown(current_question["text"]) # Use markdown for potentially formatted text

    options = current_question["options"]
    if not options:
        st.warning("옵션을 파싱할 수 없습니다. 전체 텍스트를 보여줍니다.")
        st.markdown(current_question["text"]) # Display full text without QUESTION number

        # Fallback for user input if options are not parsable
        user_answer_input = st.text_input(
            "답을 입력하세요 (예: A, AB):", 
            key=f"mock_q{current_q_index}_input", 
            value=st.session_state.user_answers[current_q_index]
        )
        st.session_state.user_answers[current_q_index] = user_answer_input.upper() # Ensure uppercase
    else:
        # Check if it's a multiple choice question based on the correct answer length
        # Assuming multi-letter answers (e.g., "AC") indicate multi-select
        if len(current_question["answer"]) > 1:
            # Multi-choice question, use st.multiselect
            default_selected = [opt for opt in options if opt[0] in st.session_state.user_answers[current_q_index]]
            selected_options_multiselect = st.multiselect(
                "정답을 선택하세요:",
                options=options,
                default=default_selected,
                key=f"mock_q{current_q_index}_multiselect"
            )
            # Store selected letters sorted to ensure consistent comparison later
            st.session_state.user_answers[current_q_index] = "".join(sorted([opt[0] for opt in selected_options_multiselect]))
        else:
            # Single-choice question, use st.radio
            initial_index = None
            if st.session_state.user_answers[current_q_index]:
                for idx, opt_text in enumerate(options):
                    if opt_text.startswith(st.session_state.user_answers[current_q_index]):
                        initial_index = idx
                        break
            
            selected_option_radio = st.radio(
                "정답을 선택하세요:",
                options=options,
                index=initial_index, # Set initial selected item
                key=f"mock_q{current_q_index}_radio"
            )
            st.session_state.user_answers[current_q_index] = selected_option_radio[0] if selected_option_radio else ""

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("이전 문제", disabled=(current_q_index == 0), key=f"mock_prev_q{current_q_index}"):
            st.session_state.current_question_index -= 1
            st.rerun()
    with col2:
        if st.button("시험 종료", help="현재까지의 답안으로 채점합니다.", key=f"mock_finish_exam"):
            st.session_state.page = "grading_page"
            st.query_params["page"] = "grading_page" # Update URL
            st.rerun()
    with col3:
        if st.button("다음 문제", disabled=(current_q_index == len(st.session_state.selected_questions) - 1), key=f"mock_next_q{current_q_index}"):
            st.session_state.current_question_index += 1
            st.rerun()

    st.markdown("---")
    if st.button("메인 화면으로 돌아가기", key="mock_to_main"):
        st.session_state.page = "main"
        st.query_params["page"] = "main" # Update URL
        # Clear mock exam related session states for a clean restart
        st.session_state.pop("selected_questions", None)
        st.session_state.pop("current_question_index", None)
        st.session_state.pop("user_answers", None)
        st.session_state.pop("start_time", None)
        st.rerun()

    # If time is still remaining and we are on the mock exam page, re-run the app after a 1-second delay
    if remaining_seconds > 0 and st.session_state.page == "mock_exam":
        time.sleep(1)
        st.rerun()

def single_question_page():
    st.header("1개씩 풀기")

    question = st.session_state.selected_question
    
    # Create a hashable version of the question for comparison
    # Convert 'options' list to a tuple to make the dictionary hashable
    hashable_question_items = []
    for k, v in question.items():
        if k == "options" and isinstance(v, list):
            hashable_question_items.append((k, tuple(v)))
        else:
            hashable_question_items.append((k, v))
    current_q_hash = hash(frozenset(hashable_question_items))

    # Initialize user_answer for the current question if not set or if it's a new question
    # Using hash to detect if the question itself has changed
    if "single_user_answer" not in st.session_state or st.session_state.get("last_single_q_hash") != current_q_hash:
        st.session_state.single_user_answer = ""
        st.session_state.last_single_q_hash = current_q_hash
        st.session_state.show_correctness = False # Hide correctness until answered

    st.subheader(f"문제 {question['number']}")
    st.markdown(question["text"]) # Use markdown for potentially formatted text

    options = question["options"]
    user_answer_for_display = st.session_state.single_user_answer

    if not options:
        st.warning("옵션을 파싱할 수 없습니다. 전체 텍스트를 보여줍니다.")
    else:
        st.markdown("---")
        st.markdown("**선택지:**")

        if len(question["answer"]) > 1: # Multi-choice question
            default_selected = [opt for opt in options if opt[0] in user_answer_for_display]
            selected_options_multiselect = st.multiselect(
                "정답을 선택하세요:",
                options=options,
                default=default_selected,
                key=f"single_q_multiselect_{question['number']}" # Unique key for each question
            )
            current_selection = "".join(sorted([opt[0] for opt in selected_options_multiselect]))
        else: # Single-choice question
            initial_index = None
            if user_answer_for_display:
                for idx, opt_text in enumerate(options):
                    if opt_text.startswith(user_answer_for_display):
                        initial_index = idx
                        break
            
            selected_option_radio = st.radio(
                "정답을 선택하세요:",
                options=options,
                index=initial_index, # Set initial selected item
                key=f"single_q_radio_{question['number']}" # Unique key for each question
            )
            current_selection = selected_option_radio[0] if selected_option_radio else ""

        # Update session state with current selection if it changed
        if current_selection != st.session_state.single_user_answer:
            st.session_state.single_user_answer = current_selection
            st.session_state.show_correctness = True # Show correctness after selection
            st.rerun() # Rerun to show correctness immediately

        if st.session_state.show_correctness:
            is_correct = sorted(list(st.session_state.single_user_answer)) == sorted(list(question["answer"]))
            if is_correct:
                st.success("정답입니다!")
            else:
                st.error("오답입니다.")

        st.markdown("---")
    
    # Answer toggle
    with st.expander("정답 보기"):
        st.success(f"정답: {question['answer']}")

    # Button to load next random question
    if st.button("다른 문제 풀기"):
        st.session_state.selected_question = random.choice(st.session_state.questions)
        st.session_state.single_user_answer = "" # Reset answer for new question
        st.session_state.show_correctness = False # Hide correctness for new question
        # Update the hash for the new question as well
        new_hashable_q_items = []
        for k, v in st.session_state.selected_question.items():
            if k == "options" and isinstance(v, list):
                new_hashable_q_items.append((k, tuple(v)))
            else:
                new_hashable_q_items.append((k, v))
        st.session_state.last_single_q_hash = hash(frozenset(new_hashable_q_items))
        st.rerun()

    if st.button("메인 화면으로 돌아가기"):
        st.session_state.page = "main"
        st.query_params["page"] = "main" # Update URL
        # Clear single question related session states for a clean restart
        st.session_state.pop("selected_question", None)
        st.session_state.pop("single_user_answer", None)
        st.session_state.pop("show_correctness", None)
        st.session_state.pop("last_single_q_hash", None)
        st.rerun()

def grading_page():
    st.header("채점 결과")

    score = 0
    total_questions = len(st.session_state.selected_questions)
    
    # Calculate score
    for i, q in enumerate(st.session_state.selected_questions):
        user_answer = st.session_state.user_answers[i]
        correct_answer = q["answer"]
        # Compare sorted lists of characters for multi-letter answers
        if sorted(list(user_answer)) == sorted(list(correct_answer)):
            score += 1

    st.markdown(f"## 점수: {score} / {total_questions}")
    st.markdown("---")

    # Display each question with results
    for i, q in enumerate(st.session_state.selected_questions):
        user_answer = st.session_state.user_answers[i]
        correct_answer = q["answer"]
        is_correct = sorted(list(user_answer)) == sorted(list(correct_answer))

        # Use st.container() with markdown for background color
        # Conditional styling based on correctness
        if not is_correct:
            st.markdown(f"<div style='background-color:#ffe0e0; padding:15px; border-radius:8px; margin-bottom:15px;'>", unsafe_allow_html=True)
            st.markdown(f"### <span style='color:red;'>문제 {q['number']} (오답)</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background-color:#e0ffe0; padding:15px; border-radius:8px; margin-bottom:15px;'>", unsafe_allow_html=True)
            st.markdown(f"### <span style='color:green;'>문제 {q['number']} (정답)</span>", unsafe_allow_html=True)


        st.markdown(f"**문제:**")
        st.write(q["text"]) # This is the main question text
        if q["options"]:
            st.write("**선택지:**")
            for opt in q["options"]:
                st.write(f"- {opt}")

        st.write(f"**당신의 답:** {''.join(sorted(list(user_answer))) if user_answer else '선택 안함'}")
        st.write(f"**정답:** {correct_answer}")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("최종 점수")
    st.markdown(f"총 {total_questions} 문제 중 **{score} 문제** 정답.")
    st.markdown(f"**점수: {round((score / total_questions) * 100, 2) if total_questions > 0 else 0}점**")

    if st.button("메인 화면으로 돌아가기", key="grade_to_main"):
        st.session_state.page = "main"
        st.query_params["page"] = "main" # Update URL
        # Clear mock exam related session states for a clean restart
        st.session_state.pop("selected_questions", None)
        st.session_state.pop("current_question_index", None)
        st.session_state.pop("user_answers", None)
        st.session_state.pop("start_time", None)
        st.rerun()


def main():
    st.set_page_config(layout="wide")
    st.title("SAA-C03 CBT")

    # Initialize session states if they don't exist
    if "questions" not in st.session_state:
        st.session_state.questions = load_questions("SAA-C03-KR v18.65_오답정정_UTF8.txt")
        st.session_state.page = "main"
        st.session_state.selected_questions = []
        st.session_state.current_question_index = 0
        st.session_state.user_answers = []
        st.session_state.start_time = None
        st.session_state.selected_question = None
        st.session_state.single_user_answer = "" # New for single question answer
        st.session_state.show_correctness = False # New for single question correctness display
        st.session_state.last_single_q_hash = None # New for detecting new single question

    # Check URL query parameters for initial page, defaulting to "main"
    current_url_page = st.query_params.get("page")
    if current_url_page and st.session_state.page != current_url_page:
        st.session_state.page = current_url_page
        if st.session_state.page == "mock_exam" and not st.session_state.selected_questions:
            num_questions_for_mock = min(65, len(st.session_state.questions))
            st.session_state.selected_questions = random.sample(st.session_state.questions, num_questions_for_mock)
            st.session_state.current_question_index = 0
            st.session_state.user_answers = ["" for _ in range(num_questions_for_mock)]
            st.session_state.start_time = time.time()
        elif st.session_state.page == "single_question" and not st.session_state.selected_question:
            st.session_state.selected_question = random.choice(st.session_state.questions)
            st.session_state.single_user_answer = ""
            st.session_state.show_correctness = False
            st.session_state.last_single_q_hash = hash(frozenset(st.session_state.selected_question.items()))
        elif st.session_state.page == "grading_page" and ("user_answers" not in st.session_state or not st.session_state.user_answers):
            # If navigating directly to grading_page via URL without mock exam data, redirect to main
            st.session_state.page = "main"
            st.query_params["page"] = "main"
            st.rerun()

    # Page routing
    if st.session_state.page == "main":
        st.write("### 메인 화면")
        if st.button("모의고사 시험 시작 (65문제, 130분)"):
            st.session_state.page = "mock_exam"
            st.query_params["page"] = "mock_exam" # Update URL
            st.session_state.selected_questions = random.sample(st.session_state.questions, 65)
            st.session_state.current_question_index = 0
            st.session_state.user_answers = [""] * len(st.session_state.selected_questions)
            st.session_state.start_time = None # Reset timer for new exam
            st.rerun()

        if st.button("1개씩 풀기"):
            st.session_state.page = "single_question"
            st.query_params["page"] = "single_question" # Update URL
            st.session_state.selected_question = random.choice(st.session_state.questions) # Select a random question for single mode
            st.rerun()

    elif st.session_state.page == "mock_exam":
        mock_exam_page()
    elif st.session_state.page == "single_question":
        single_question_page()
    elif st.session_state.page == "grading_page":
        grading_page()

if __name__ == "__main__":
    main() 