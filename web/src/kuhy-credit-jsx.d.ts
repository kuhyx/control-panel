// React 19 reads React.JSX, not the global JSX namespace that
// @kuhyx/kuhy-credit's typings extend, so register the tag here too.
import type { KuhyCreditAttributes } from "@kuhyx/kuhy-credit";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "kuhy-credit": KuhyCreditAttributes & { class?: string };
    }
  }
}
