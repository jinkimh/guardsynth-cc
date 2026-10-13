"""Synchronize response excerpts with current sources; preserve reviewer comments."""
import json
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parent


def resolve_references(text):
    """Use the article's numbers in standalone responses without a bibliography."""
    auxiliary = (SOURCE / "main.aux").read_text()
    citations = dict(re.findall(r"\\bibcite\{([^}]+)\}\{([^}]+)\}", auxiliary))
    labels = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}", auxiliary))
    text = re.sub(r"\\cite\{([^}]+)\}",
                  lambda match: "[" + ", ".join(citations[key] for key in match[1].split(",")) + "]", text)
    return re.sub(r"\\ref\{([^}]+)\}", lambda match: labels[match[1]], text)

# Reviewer order is fixed: Major 1-6, Minor 1-3; R2 1.1/1.2/2-7; R3 1-11.
QUOTES = [
    ("10-conclusion", "현재 결과는 명시된 프레임", 1, "sec:conclusion"),
    ("05-method", "기존 자동 변환은", 2, "sec:extraction"),
    ("07-results", "AC1 추가 재분석은", 2, "sec:human-results"),
    ("07-results", "FSM은 144/144", 2, "sec:first-results"),
    ("07-results", "탐지 대상 130건을", 2, "sec:trajectory-results"),
    ("03-data", "CoC-Nusc의 배포 버전", 1, "sec:provenance"),
    ("03-data", "후보 선택기는", 2, "sec:provenance"),
    ("03-data", "309는 후보 선정에", 2, "sec:provenance"),
    ("10-conclusion", "작성된 미해제 충돌 사례에서는", 2, "sec:conclusion"),
    ("01-introduction", "두 문장은 각각 자연스럽지만", 2, "sec:intro"),
    ("01-introduction", "이러한 불일치 때문에", 1, "sec:intro"),
    ("01-introduction", "본 연구는 이를 위해", 5, "sec:intro"),
    ("01-introduction", "UPPAAL은 웁살라", 1, "sec:intro"),
    ("01-introduction", "본 논문의 연구 질문은", 2, "sec:intro"),
    ("01-introduction", "본 연구는 이를 위해", 3, "sec:intro"),
    ("02-related-work", "기존 연구는 한 장면의 설명과", 2, "sec:related-position"),
    ("01-introduction", "원문 구절, 의무, 해제 조건과", 1, "sec:intro"),
    ("02-related-work", "실행 중 검증(runtime verification)은", 3, "sec:related-rv"),
    ("03-data", "보조 반응 분석에서는", 2, "sec:provenance"),
    ("04-problem", "P1--P3은", 3, "sec:error-types"),
    ("04-problem", "갱신 순서는 경계 정책", 3, "sec:boundary-semantics"),
    ("05-method", "True/False는 작성 문장이", 1, "sec:extraction"),
    ("05-method", "조건 연결 모델은 committed 위치", 1, "sec:queries"),
    ("07-results", "이 시험은 기대 결과에", 2, "sec:bounded-results"),
    ("07-results", "FSM은 144/144", 2, "sec:first-results"),
    ("07-results", "범주 편중에 따른 보정 민감도이며", 2, "sec:human-results"),
    ("07-results", "합계 40/40과 20/40을", 1, "sec:regression-results"),
    ("07-results", "27장면의 궤적 비교는", 1, "sec:trajectory-results"),
]
SUPPLEMENTS = {
    "R1-M1": "별도 81건의 장면 경계 시험도 본문에 통합했습니다. 유지 모델은 81/81, 초기화는 14/81입니다. 초기화 모델은 확정 모순 41/44와 근거 부족 26/29를 양립으로 판정했습니다. 두 결과는 작성 시험입니다. 선별 없는 유한 범위의 35,042,928건을 별도 수식 계산과 고정 XML의 상태 갱신 코드로 비교한 결과 불일치 0이었지만, 이는 명세 적합성의 부분 근거이며 자연 오류 성능이나 외부 독립 의미 정답이 아닙니다.",
    "R1-M2": "자연 CoC 90장면의 원문 399건에 대한 파서 집계를 추가했습니다. 행동 인식 원문은 230건, 미인식은 169건이며 265단계 중 구문 해석 완료 219·대상 누락 44·순서 모호 2건입니다. until 해제 조건은 0건, once/after 계기는 10건입니다. scene-0051의 실제 문장은 자동 처리 사례로 별도 제시했습니다. 이는 구문 처리 집계이지 의미 추출 정확도가 아닙니다. 별도 81건은 원 자연어 구절이 없는 기호 입력이며, 대상 동일성·적용 범위·증거 유효성은 설계자 제공 값입니다.",
    "R1-M3": "원 4인×27장면의 AC1을 추가 재분석했습니다. 시간 요구 0.627, 행동열 0.323, 텍스트 0.301이며 기존 κ를 대체하지 않습니다. 시간 요구는 YES 81/108의 범주 편중으로 우연 일치 항에 민감합니다. 텍스트의 원시 일치 0.407과 불일치 23/27은 그대로이고, 행동열은 39관측 문자열 범주에 조건부입니다. 새 사람 평가·지침 개선 효과·자격/교육/합의 기록 복원을 주장하지 않습니다.",
    "R1-M4": "81건의 유지/초기화 비교는 경계 기억의 제거 비교로 추가했습니다. FSM과 이전 N개 사건 창의 144건 비교를 대체하지 않으며, 다른 자료의 수치를 합쳐 정확도 우위를 계산하지 않습니다. 전체 문장열 LLM 판정기는 후속 작업으로 남아 있습니다.",
    "R1-M6": "신규 경계 시험과 유한 범위 적합성 시험에는 입력 프로토콜, 고정 소스·XML·판정기 해시, 전체 생성 규칙과 불일치를 보존했습니다. 적합성 시험은 실제 XML에서 추출한 상태 갱신 코드를 C++로 직접 실행한 것으로서 UPPAAL 탐색기를 새로 실행했다는 뜻은 아닙니다. 과거 생성 모델·prompt/config와 검토자 기록의 결손은 그대로 인정합니다.",
    "R2-4": "현재 첫 질문은 의무·해제 근거 연결과 문제 추적으로, 144건 비교 및 동일 사례 재시험에 대응합니다. 둘째 경계 질문은 유지/종료·근거 만료·재활성화 정책으로, 별도 81건에 대응합니다. 유한 범위 전수 대조는 이 의미 명세의 구현 적합성을 보강하며 별도의 자연 성능 기여로 계산하지 않습니다.",
    "R2-5": "서론을 배경·문제·실제 기록의 장면 경계 동기·기존 연구·접근 방법·연구 질문·기여·평가 범위·논문 구성의 순서로 갱신했습니다. 네 평가의 핵심 결과를 구분해 요약하고, 경계 정책·배열·질의와 상세 수치는 방법과 결과 절에서 설명했습니다.",
    "R3-3": "전수 적합성 시험에서도 P4는 참 증거로 해제된 활성 의무를 잘못 남기는 처리 고장으로 별도 주입했습니다. 길이 1–2의 5,256건 중 상태 불일치 1,884건을 보존했고 주 시험 분모에 합산하지 않았습니다. 입력 생애주기의 재활성화와 P4 코드 고장을 구분했습니다.",
    "R3-4": "경계 확장 모델의 VERIFIED/ENDED/UNCERTAIN, 순간 관측 만료, 지속 구간 근거, 재활성화 초기화를 본문에 추가했습니다. 24건에서 확정 모순과 근거 부족이 함께 발생했고 두 기록을 보존하며 최종 판정은 확정 모순을 우선했습니다. 대상·범위는 제공된 입력이며 영상에서 자동 추적한 결과가 아닙니다.",
    "R3-5": "자연 CoC 90장면·399원문의 자동 파서 집계와 scene-0051의 실제 처리 사례를 추가했습니다. 265개 행동 단계 중 구문 해석 완료는 219개이며, 해제 조건을 찾거나 조건의 참·거짓을 확정한 성능으로 해석하지 않습니다. scene-0051 문장 하나의 기존 검사 출력은 양립이지만 후속 진행이 없어 충돌을 검사하지 않은 경우임을 함께 밝혔습니다. 자연 문장 자동 처리와 설계자 작성 프레임 사례를 같은 표의 (a)/(b)로 나눴습니다.",
    "R3-6": "신규 81건의 배열·경계 갱신과 종료 시점의 확정 모순ㆍ근거 부족 질의를 기존 144건 모델과 구분했습니다. 추가 전수 시험은 고정 XML의 상태 갱신 코드를 C++로 실행하고 전체 접두열에서 계산하는 별도 수식 판정과 상태·누적 문제·최초 사건/의무를 대조한 것입니다. 35,042,928건 불일치 0은 유한 범위의 구현 적합성이지 규칙의 현실 타당성이나 UPPAAL 탐색 엔진의 새 검증이 아닙니다.",
    "R3-9": "기존 원 라벨을 유지한 AC1 재분석을 추가했습니다(시간 요구/행동열/텍스트 0.627/0.323/0.301). 범주 집합과 원시 일치·기존 κ를 함께 보고, 더 큰 계수만 선택하지 않았습니다. 자격·교육·합의 사유의 기록 결손과 사람 재평가 미실시는 그대로 남깁니다.",
    "R3-10": "81건의 확정 모순 44/근거 부족 29/양립 8 및 초기화 혼동행렬도 작성 시험으로 보고했습니다. 35,042,928건은 열거한 조합의 수이며 자연 모집단 성능의 분모가 아닙니다. 독립 자연 의미 정답이 없어 자연 P/R/F1을 산출하지 않았습니다.",
    "R3-11": "81건의 작성 경계 결과는 자연 궤적 2/7/18을 대체하지 않습니다. 보관된 장면 연결 후보(13개 구간, 16개 경계)에는 세 조건의 동일 대상·적용 범위·해제 참값 연결이 없어 자연 장면 간 의미 검증도 미실시로 명시했습니다.",
}
R3_7 = """사례 선별의 순환성에 대한 지적을 수용했습니다. 기존 40쌍은 기대 결과를 확인한 회귀시험으로 남기고, 144건의 최초 실패 48건 및 개발 후 동일 사례 재시험과 별도로 선별 없는 유한 범위 전수 시험을 추가했습니다.

두 모델 소스·실행 당시 명세·생성기·수식 판정기를 먼저 해시로 고정했습니다. 실행 당시 명세는 해시가 일치하는 재현 입력으로 보존하며 현재 4장은 두 모델의 의미 차이와 적용 범위를 명확히 했습니다. 행동, 의무 생성과 조건 증거의 선언된 조합을 모두 생성했고 기대 판정은 손으로 쓰지 않았습니다. 별도 판정기는 전체 접두열의 최근 증거·생성·해제를 직접 계산하며 상태 갱신 함수를 공유하지 않습니다. 고정 XML에서 추출한 상태 갱신 코드를 C++로 직접 실행한 결과와 수식 판정기의 출력을 상태·누적 문제·최초 사건/의무별로 비교했습니다. 각 모델과 해당 명세의 35,042,928건 대조에서 불일치가 없었습니다. 두 모델 사이의 동등성 시험은 아닙니다. P4 처리 고장의 별도 5,256건에서는 1,884건의 상태 불일치를 모두 보존했습니다. 결과에 따라 사례를 빼거나 정답을 수정하지 않았습니다.

이는 사례 선별 편향과 하나의 계산 경로에 대한 의존을 줄인 부분 대응입니다. 두 경로에 같은 연구 작성자가 관여했고 명세 자체의 공통 오류가 남을 수 있습니다. 유한 상한 밖의 사건열, 독립 자연 의미 정답 및 외부 작성 평가를 입증하지 않으며 UPPAAL 탐색기를 새로 실행한 시험도 아닙니다. 81건 역시 설계자 작성 시험으로 구분합니다. 독립 시험 요구를 완전히 충족했다고 주장하지 않습니다."""


def main():
    ids = [f"R1-M{i}" for i in range(1, 7)] + [f"R1-m{i}" for i in range(1, 4)]
    ids += ["R2-1.1", "R2-1.2"] + [f"R2-{i}" for i in range(2, 8)]
    ids += [f"R3-{i}" for i in range(1, 12)]
    descriptors = dict(zip(ids, QUOTES))
    metadata, offset = {}, 0
    for reviewer, count in [(1, 9), (2, 8), (3, 11)]:
        path = SOURCE / f"response-to-reviewer-{reviewer}.tex"
        text = path.read_text()
        comments_before = re.findall(r"\\begin\{reviewercomment\}(.*?)\\end\{reviewercomment\}", text, re.S)
        items = list(re.finditer(r"\\begin\{reviewitem\}.*?\\end\{reviewitem\}", text, re.S))
        assert len(items) == count
        for local, match in reversed(list(enumerate(items))):
            identity = ids[offset + local]
            block = match.group()
            name, anchor, sentences, label = descriptors[identity]
            source_path = SOURCE / "sections" / (name + ".tex")
            line = next(line for line in source_path.read_text().splitlines() if anchor in line)
            line = line[line.index(anchor):]
            quote = " ".join(re.split(r"(?<=\.)\s+", line)[:sentences])
            assert quote in source_path.read_text(), identity
            label_text = (SOURCE / ("sections/" + name + ".tex")).read_text()
            assert "\\label{" + label + "}" in label_text, (identity, label)
            rendered = resolve_references(quote)
            metadata[identity] = {"source": str(source_path.relative_to(SOURCE)), "label": label,
                                  "quote": quote, "rendered_quote": rendered}
            body = re.search(r"\\begin\{authorresponse\}(.*?)\\end\{authorresponse\}", block, re.S).group(1)
            body = re.sub(r"\n% Supplemental evidence.*?% End supplemental evidence\n", "\n", body, flags=re.S)
            if identity == "R3-7":
                body = "\n\n" + R3_7 + "\n\n"
            elif identity in SUPPLEMENTS:
                if identity == "R2-4":
                    body = "\n\n연구 질문을 두 가지로 명시했습니다. RQ1은 의무와 해제 근거를 연결해 확정 모순과 근거 부족을 구분하고 최초 문제를 추적할 수 있는가, RQ2는 장면 경계에서 의무와 증거를 유지하는 정책이 판정을 어떻게 바꾸는가입니다. 서론의 네 기여에는 대응하는 연구 질문을 표시했습니다. 중간표현과 판정 규칙은 RQ1, 경계 입력 조건은 RQ2, UPPAAL 구현과 비교·경계·전수 시험은 두 질문 모두에 대응합니다. 결론도 두 질문의 답을 차례로 정리하도록 다시 썼습니다. 평가 결과 자체를 독립적인 알고리즘 기여로 세지 않습니다.\n\n"
                body = body.rstrip() + "\n\n% Supplemental evidence 2026-10-12\n" + SUPPLEMENTS[identity] + "\n% End supplemental evidence\n\n"
            block = re.sub(r"(\\begin\{authorresponse\}).*?(\\end\{authorresponse\})", lambda m: m[1] + body + m[2], block, count=1, flags=re.S)
            revision = (r"\begin{manuscriptrevision}{\mloc{" + label + r"}; 발췌: \quotepages{" + identity + "}}\n"
                        + "본문의 실제 수정 문장은 다음과 같습니다.\n\n" + r"\begin{quote}" + "\n" + rendered + "\n" + r"\end{quote}" + "\n" + r"\end{manuscriptrevision}")
            block = re.sub(r"\\begin\{manuscriptrevision\}.*?\\end\{manuscriptrevision\}", lambda _: revision, block, count=1, flags=re.S)
            text = text[:match.start()] + block + text[match.end():]
        comments_after = re.findall(r"\\begin\{reviewercomment\}(.*?)\\end\{reviewercomment\}", text, re.S)
        assert comments_before == comments_after
        path.write_text(text)
        offset += count
    (SOURCE / "response_excerpt_sources.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print("Synchronized 28 excerpts; all reviewer comments unchanged")


if __name__ == "__main__":
    main()
