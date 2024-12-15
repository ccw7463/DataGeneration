from openai import OpenAI
from datasets import load_dataset
import json
import multiprocessing
from tqdm import tqdm

class DataGenerator:
    def __init__(self):
        self.openai_api_key = "EMPTY"
        self.openai_api_base = "http://192.168.1.20:1318/v1"
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base,
        )
        self.USE_MODEL = "pixtral"
        self.MODEL_NAME_DICT = {
            "qwen": "Qwen/Qwen2-VL-72B-Instruct",
            "pixtral": "mistralai/Pixtral-Large-Instruct-2411"
        }
        self.MODEL_NAME = self.MODEL_NAME_DICT[self.USE_MODEL]
        self.SYSTEM_PROMPT_DICT = {
            "qwen": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
            "pixtral": "You are a helpful assistant."
        }
        self.SYSTEM_PROMPT = self.SYSTEM_PROMPT_DICT[self.USE_MODEL]

    def LLM_Call(self, 
                 prompt: str) -> str:
        chat_response = self.client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"{prompt}"},
            ],
            temperature=0.001,
            top_p=0.001,
            max_tokens=4096,
            extra_body={
                "repetition_penalty": 1.03,
            },
        )
        return chat_response.choices[0].message.content


def get_question(context: str) -> str:
    prompt = f"""당신은 데이터 생성 전문가입니다.
    
    보안 관련 질의 데이터 1개를 만들어야합니다.
    영어로 표기해야하는 전문 용어만 영어를 사용합니다.
    영어로 표기해야하는 전문 용어가 아닐경우 무조건 질의는 한국어로 생성합니다.
    [Context]을 참고해서 질의 데이터 1개를 만들어주세요. 무조건 질의 문장만 생성합니다.
    
    [Context]
    {context}
    """
    return prompt

def get_answer(question: str,
               context: str) -> str:
    prompt = f"""당신은 데이터 생성 전문가입니다.
    
    보안 관련 응답 데이터를 만들어야합니다.
    영어로 표기해야하는 전문 용어만 영어를 사용합니다.
    영어로 표기해야하는 전문 용어가 아닐경우 무조건 응답은 한국어로 생성합니다.
    [Context]을 참고해서, [Question]에 대한 응답 데이터를 만들어주세요. 무조건 응답 문장만 생성합니다.
    
    [Context]
    {context}
    
    [Question]
    {question}
    """
    return prompt

def split_indices(start: int, end: int, num_splits: int):
    step = (end - start + 1) // num_splits
    indices = []
    for i in range(num_splits):
        sub_start = start + i * step
        sub_end = start + (i + 1) * step - 1 if i < num_splits - 1 else end
        indices.append((sub_start, sub_end))
    return indices

def process_data(start_idx: int, end_idx: int, output_file: str, queue: multiprocessing.Queue):
    data_generator = DataGenerator()
    dataset = load_dataset("PNU-Infosec/cipher-context-dataset", "cipher", split="train")
    parallel_dataset = dataset.select(range(start_idx, end_idx + 1))
    total = len(parallel_dataset)
    print(f"Processing data from {start_idx} to {end_idx}...")

    JSON_DATA = []
    for idx, data in enumerate(tqdm(parallel_dataset)):
        try:
            question_prompt = get_question(context=data['output'])
            question = data_generator.LLM_Call(question_prompt)
            answer_prompt = get_answer(question=question, context=data['output'])
            answer = data_generator.LLM_Call(answer_prompt)
            JSON_DATA.append({
                "instruction": question.strip(),
                "output": answer.strip()
            })
        except Exception as e:
            print(f"Error at index {idx}: {e}")
            continue
        
        # 🔥 전체 프로세스 진행 상황을 Queue에 전달
        queue.put(1) 

        if (idx % 500 == 0) or (idx == 10):
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(JSON_DATA, f, ensure_ascii=False, indent=4)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(JSON_DATA, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {output_file}")


if __name__ == '__main__':
    start_idx = 0
    end_idx = 36022
    num_splits = 100

    index_ranges = split_indices(start_idx, end_idx, num_splits)
    jobs = [
        {'start_idx': start, 'end_idx': end, 'output_file': f'data/cipher_data_parallel_version_{i+1}.json'}
        for i, (start, end) in enumerate(index_ranges)
    ]

    processes = []
    queue = multiprocessing.Queue()

    total_work = sum(end - start + 1 for start, end in index_ranges)

    # 🔥 메인 프로세스에 tqdm 추가 (전체 진행 상황 추적)
    with tqdm(total=total_work, desc="Total Progress") as pbar:
        for job in jobs:
            p = multiprocessing.Process(
                target=process_data, 
                args=(job['start_idx'], job['end_idx'], job['output_file'], queue)
            )
            processes.append(p)
            p.start()

        while any(p.is_alive() for p in processes):
            # 🔥 모든 프로세스의 진행 상황을 반영
            while not queue.empty():
                pbar.update(queue.get())
        
        for p in processes:
            p.join()

    print("All jobs have finished processing.")
