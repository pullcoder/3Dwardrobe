import { Notice, PageHeading, Panel } from "../components/UI";
import { AccountPanel } from "../features/garments/AccountPanel";
import { useSession } from "../stores/SessionContext";
import { RecommendationWorkspace } from "../features/recommendations/RecommendationWorkspace";

export function RecommendPage() {
  const { auth } = useSession();
  return (
    <>
      <PageHeading
        eyebrow="STYLE, YOUR WAY"
        title="AI 코디 추천"
        description="내 옷장과 취향으로 만드는 스타일 제안"
      />
      <Notice>
        현재 추천 방식은 규칙 기반입니다. 실제 보유 의류만 조합하며, 점수는 착용
        만족도나 패션 품질을 뜻하지 않습니다. 외부 AI에 사진을 전송하지
        않습니다.
      </Notice>
      <AccountPanel />
      {auth ? (
        <RecommendationWorkspace key={auth.token} token={auth.token} />
      ) : (
        <Panel title="로그인 후 내 옷장으로 추천받기">
          <p>체형 분석 없이 취향과 저장한 의류만으로도 추천할 수 있습니다.</p>
        </Panel>
      )}
    </>
  );
}
