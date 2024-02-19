import json

def simplified_extract_text(message):
    if isinstance(message['text'], str):
        return message['text']
    elif isinstance(message['text'], list):
        full_text = []
        for text_component in message['text']:
            if isinstance(text_component, dict) and 'text' in text_component:
                full_text.append(text_component['text'])
            elif isinstance(text_component, str):
                full_text.append(text_component)
        return " ".join(full_text)
    return ""

def main():
    file_path = 'source/result.json'
    # Specify encoding='utf-8' when reading the file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    questions = {}
    answers = {}

    for message in data['messages']:
        if 'forwarded_from' in message:
            question_id = message['id']
            question_text = simplified_extract_text(message)
            questions[question_id] = question_text
        elif 'reply_to_message_id' in message:
            reply_to_id = message['reply_to_message_id']
            extracted_text = simplified_extract_text(message)
            if reply_to_id in answers:
                answers[reply_to_id] += " " + extracted_text
            else:
                answers[reply_to_id] = extracted_text

    qa_pairs_simplified = []
    for q_id, question_text in questions.items():
        answer = answers.get(q_id, "No answer found")
        qa_pairs_simplified.append({'Question': question_text, 'Answer': answer})

    # Specify encoding='utf-8' when writing the file
    with open('data/qa.json', 'w', encoding='utf-8') as file:
        json.dump(qa_pairs_simplified, file, ensure_ascii=False, indent=4)

    print("Done. Extracted", len(qa_pairs_simplified), "question-answer pairs.")        

if __name__ == "__main__":
    main()
