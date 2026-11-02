import { useState } from "react";
import { Sparkles } from "lucide-react";
import {
  ComingButton,
  EmptyState,
  Notice,
  PageHeading,
  Panel,
} from "../components/UI";

export function RecommendPage() {
  const [style, setStyle] = useState("minimal");
  const [fit, setFit] = useState("regular");
  const [purpose, setPurpose] = useState("daily");
  return (
    <>
      <PageHeading
        eyebrow="STYLE, YOUR WAY"
        title="AI 코디 추천"
        description="평가가 아닌 제안. 나의 취향과 일상을 위한 스타일을 준비해요."
      />
      <Notice>
        추천 엔진은 6단계에서 연결합니다. 추천 코디·이미지·점수를 임의로
        생성하지 않습니다. 아래 선택은 화면을 벗어나면 초기화됩니다.
      </Notice>
      <Panel
        title="어떤 스타일을 찾고 있나요?"
        subtitle="신체의 미적 등급을 매기지 않고 선호와 목적을 바탕으로 제안할 예정입니다."
      >
        <div className="form-grid three-col">
          <label className="field">
            <span>선호 스타일</span>
            <select
              value={style}
              onChange={(event) => setStyle(event.target.value)}
            >
              <option value="minimal">미니멀</option>
              <option value="casual">캐주얼</option>
              <option value="street">스트릿</option>
              <option value="classic">클래식</option>
            </select>
          </label>
          <label className="field">
            <span>선호하는 핏</span>
            <select
              value={fit}
              onChange={(event) => setFit(event.target.value)}
            >
              <option value="regular">레귤러 핏</option>
              <option value="relaxed">여유 있는 핏</option>
              <option value="fitted">몸에 맞는 핏</option>
            </select>
          </label>
          <label className="field">
            <span>착용 목적</span>
            <select
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
            >
              <option value="daily">편안한 일상</option>
              <option value="work">출근 / 미팅</option>
              <option value="occasion">특별한 약속</option>
            </select>
          </label>
        </div>
        <ComingButton>
          <Sparkles size={17} />
          AI 코디 추천
        </ComingButton>
      </Panel>
      <section className="panel">
        <EmptyState title="나의 취향이 스타일이 되는 곳">
          추천 기능을 연결하면 보유 의류로 구성한 3~5개 코디와
          <br />
          추천 이유, 3D 입어보기, 코디 저장을 제공합니다.
        </EmptyState>
      </section>
    </>
  );
}
