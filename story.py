import json
from pathlib import Path
from llama_cpp import Llama

# 1. Llama 모델 초기화 (모델 경로와 옵션은 실제 환경에 맞게 수정하세요)
llm = Llama(
    model_path="./models/llama-3.2-Korean-Bllossom-3B-gguf-Q4_K_M.gguf",
    n_ctx=2048,       # 컨텍스트 길이 (필요에 따라 조정)
    n_threads=8,     # CPU 스레드 수 (시스템에 맞게 조정)
    verbose=False    # 디버그 메시지 비활성화
)

class DialogueManager:
    def __init__(self, history_file: str = "dialogue_history.json"):
        self.history_file = history_file
        self.history = self.load_history()
    
    def load_history(self) -> list:
        if Path(self.history_file).exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def add_dialogue(self, speaker: str, text: str, type: str = "dialogue"):
        self.history.append({
            "speaker": speaker,
            "text": text,
            "type": type
        })
        self.save_history()
    
    def get_recent_context(self, n_turns: int = 5) -> str:
        """최근 n_turns 만큼의 대화 내용만 반환"""
        context = ""
        for entry in self.history[-n_turns:]:
            if entry["type"] == "narration":
                context += f"{entry['text']}\n"
            else:
                context += f"{entry['speaker']}: {entry['text']}\n"
        return context

# 2. 페르소나 캐릭터 클래스 정의
class PersonaCharacter:
    def __init__(self, name: str, persona_prompt: str, example_dialogues: list, model: Llama, dialogue_manager: DialogueManager):
        self.name = name
        self.persona_prompt = persona_prompt
        self.example_dialogues = example_dialogues
        self.model = model
        self.dialogue_manager = dialogue_manager

    def clean_response(self, text: str) -> str:
        """응답 텍스트를 정제하는 함수"""
        # 숫자와 특수문자 제거
        text = ''.join(char for char in text if not char.isdigit())
        text = text.replace("'", "").replace('"', "")
        
        # 불필요한 텍스트 제거
        text = text.replace("나레이션:", "").replace("토끼:", "").replace("거북이:", "")
        text = text.replace("대사:", "").replace("상황:", "")
        
        # 한글과 기본 문장부호만 허용
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ가나다라마바사아자차카타파하 .,!?~')
        text = ''.join(char for char in text if char in allowed_chars)
        
        # 감탄사 정리 (한 번만 사용)
        if "흐흐" in text:
            text = text.replace("흐흐", "흐흐", 1)
            text = text.replace("흐흐", "")
        
        # 문장 정리
        text = text.strip()
        if not text.endswith((".", "!", "?")):
            text = text + "."
            
        # 따옴표 추가
        text = f'"{text}"'
        
        return text

    def chat(self, input_text: str, max_tokens: int = 150) -> str:
        recent_context = self.dialogue_manager.get_recent_context(n_turns=3)
        
        system_prompt = (
            f"당신은 {self.name}입니다. {self.persona_prompt}\n"
            f"다음 규칙을 반드시 따르세요:\n"
            f"1. 한 문장만 말하세요.\n"
            f"2. 한글만 사용하세요.\n"
            f"3. 다른 캐릭터를 언급하지 마세요.\n"
            f"4. 나레이션이나 지시문을 포함하지 마세요.\n"
            f"5. 감정을 직접적으로 표현하지 마세요.\n"
            f"6. 토끼는 '~야', '~지', '~네' 등의 반말을, 거북이는 '~입니다', '~습니다' 등의 존댓말을 사용하세요.\n"
        )
        
        chat_prompt = (
            f"대화 예시:\n"
            + "\n".join([f"상황: {ex['situation']}\n대사: {ex['dialogue']}" for ex in self.example_dialogues])
            + f"\n\n최근 대화:\n{recent_context}\n"
            f"현재 상황: {input_text}\n"
            f"다음 대사: "
        )
        
        prompt = system_prompt + "\n\n" + chat_prompt
        
        response = self.model(prompt=prompt, max_tokens=max_tokens)
        response_text = response["choices"][0]["text"].strip()
        
        cleaned_response = self.clean_response(response_text)
        self.dialogue_manager.add_dialogue(self.name, cleaned_response)
        return cleaned_response

# 캐릭터별 예시 대화
rabbit_examples = [
    {
        "situation": "거북이를 처음 만난 상황",
        "dialogue": "거북이야, 너 정말 느리게 걷는구나! 나랑 한번 경주해볼래?"
    },
    {
        "situation": "자신의 빠른 속도를 자랑하는 상황",
        "dialogue": "흐흐, 내가 저기까지 가는 건 눈 깜빡할 사이라구!"
    },
    {
        "situation": "거북이를 놀리는 상황",
        "dialogue": "이렇게 느린 걸음으로는 언제 도착할지 모르겠네! 흐흐!"
    }
]

turtle_examples = [
    {
        "situation": "토끼의 제안에 처음 반응하는 상황",
        "dialogue": "그렇게 서두르지 않아도 된다고 생각합니다만..."
    },
    {
        "situation": "자신의 페이스를 유지하려는 상황",
        "dialogue": "천천히 가더라도 포기하지 않고 끝까지 가보도록 하죠."
    },
    {
        "situation": "토끼의 자만심에 대응하는 상황",
        "dialogue": "빠르기만 한 것이 좋은 것은 아니라고 생각합니다."
    }
]

# 3. 각 캐릭터의 페르소나 정의
rabbit_persona = (
    "당신은 자신감 넘치고 빠른 토끼입니다. "
    "성격이 경쾌하고 자신만만하며, 거북이를 약간 얕보는 태도를 보입니다. "
    "반드시 반말을 사용하며 '~야', '~지', '~구나', '~네' 등의 어미를 씁니다. "
    "'흐흐'나 '하하' 같은 웃음소리를 자주 넣습니다. "
    "거북이의 느린 걸음을 놀리고 자신의 빠른 속도를 자랑합니다."
)

turtle_persona = (
    "당신은 느리지만 지혜로운 거북이입니다. "
    "반드시 존댓말을 사용하며 '~입니다', '~습니다', '~요' 등의 어미를 씁니다. "
    "차분하고 신중한 성격이며, 토끼가 자신을 얕보더라도 결코 흥분하지 않습니다. "
    "자신의 페이스를 잃지 않고 침착하게 대응하며, 빠른 것보다 꾸준한 것이 중요함을 강조합니다."
)

class NarrationManager(PersonaCharacter):
    def __init__(self, dialogue_manager: DialogueManager, model: Llama):
        super().__init__(
            name="나레이션",
            persona_prompt=(
                "당신은 토끼와 거북이 이야기의 나레이터입니다. "
                "등장인물들의 대화와 행동을 관찰하고 상황을 자연스럽게 설명합니다. "
                "항상 객관적이고 차분한 톤을 유지하며, 이야기의 흐름을 자연스럽게 이끌어갑니다."
            ),
            example_dialogues=[
                {
                    "situation": "토끼가 거북이를 만난 후",
                    "dialogue": "거북이는 토끼의 제안을 듣고 천천히 고개를 끄덕였습니다."
                },
                {
                    "situation": "경주 중간 상황",
                    "dialogue": "토끼는 자신의 빠른 속도를 과신한 나머지, 나무 그늘에서 휴식을 취하기로 했습니다."
                }
            ],
            model=model,
            dialogue_manager=dialogue_manager
        )

    def narrate(self, situation: str) -> str:
        """현재 상황을 바탕으로 나레이션 생성"""
        recent_context = self.dialogue_manager.get_recent_context(n_turns=3)
        
        system_prompt = (
            "당신은 이야기의 나레이터입니다.\n"
            "다음 규칙을 반드시 따르세요:\n"
            "1. 등장인물들의 대화를 바탕으로 상황을 자연스럽게 설명하세요.\n"
            "2. 감정이나 분위기를 섬세하게 표현하세요.\n"
            "3. 이야기의 흐름을 자연스럽게 이어가세요.\n"
            "4. 한 문단으로 간결하게 설명하세요.\n"
            "5. 객관적인 시점을 유지하세요.\n"
        )
        
        prompt = (
            f"{system_prompt}\n\n"
            f"최근 대화:\n{recent_context}\n"
            f"현재 상황: {situation}\n"
            f"나레이션: "
        )
        
        response = self.model(prompt=prompt, max_tokens=150)
        response_text = response["choices"][0]["text"].strip()
        
        cleaned_response = self.clean_response(response_text)
        self.dialogue_manager.add_dialogue(self.name, cleaned_response, "narration")
        return cleaned_response

def simulate_story():
    dialogue_manager = DialogueManager()
    
    rabbit = PersonaCharacter("토끼", rabbit_persona, rabbit_examples, llm, dialogue_manager)
    turtle = PersonaCharacter("거북이", turtle_persona, turtle_examples, llm, dialogue_manager)
    narrator = NarrationManager(dialogue_manager, llm)
    
    # 스토리 시작
    story_state = {
        "phase": "introduction",  # introduction, development, climax, resolution
        "location": "숲속",
        "current_situation": "평화로운 오후"
    }
    
    while True:
        # 현재 상황에 맞는 나레이션 생성
        narration_prompt = f"{story_state['location']}에서 {story_state['current_situation']}의 모습"
        narration = narrator.narrate(narration_prompt)
        print("\n나레이션: " + narration)
        
        # 현재 상황 분석
        recent_context = dialogue_manager.get_recent_context(n_turns=3)
        
        # 스토리 단계별 진행
        if story_state["phase"] == "introduction":
            rabbit_prompt = "거북이를 보고 경주를 제안하고 싶은 마음이 듭니다"
            turtle_prompt = "토끼의 갑작스러운 제안을 듣고 있습니다"
            story_state["phase"] = "development"
            
        elif story_state["phase"] == "development":
            if "경주" in recent_context:
                rabbit_prompt = "경주가 시작되어 신나게 달리고 있습니다"
                turtle_prompt = "자신의 페이스로 천천히 전진합니다"
                story_state["phase"] = "climax"
                
        elif story_state["phase"] == "climax":
            if "앞서" in recent_context or "빠르" in recent_context:
                rabbit_prompt = "너무 앞서가서 잠시 쉬고 싶은 마음이 듭니다"
                turtle_prompt = "묵묵히 전진하고 있습니다"
                story_state["phase"] = "resolution"
                
        elif story_state["phase"] == "resolution":
            if "잠" in recent_context or "쉬" in recent_context:
                rabbit_prompt = "잠에서 깨어나 놀란 상황입니다"
                turtle_prompt = "결승선이 보이는 상황입니다"
                break
        
        # 캐릭터 대화 생성
        rabbit_line = rabbit.chat(rabbit_prompt)
        print("\n토끼: " + rabbit_line)
        
        turtle_line = turtle.chat(turtle_prompt)
        print("\n거북이: " + turtle_line)
        
        # 상황 업데이트
        story_state["current_situation"] = f"토끼와 거북이의 대화 이후"
    
    # 이야기 마무리
    final_narration = narrator.narrate("이야기의 교훈과 마무리")
    print("\n나레이션: " + final_narration)

if __name__ == "__main__":
    simulate_story()