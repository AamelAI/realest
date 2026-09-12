import { Board } from "@/components/Board";
import { MOCK_STATE } from "@/lib/mock";

/**
 * Template preview. Static mock data, polling off — this is how you review the
 * design without a phone in your hand. The real surface is /s/[sid].
 */
export default function TemplatePage() {
  return <Board sid="" initial={MOCK_STATE} live={false} />;
}
