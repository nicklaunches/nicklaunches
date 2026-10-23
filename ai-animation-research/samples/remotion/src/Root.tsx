import {Composition} from 'remotion';
import {Explainer3D} from './Explainer3D';
import {Explainer2D} from './Explainer2D';
export const Root = () => (
  <>
    <Composition id="Explainer3D" component={Explainer3D} durationInFrames={720} fps={30} width={1080} height={1920} />
    <Composition id="Explainer2D" component={Explainer2D} durationInFrames={600} fps={30} width={1080} height={1920} />
  </>
);
