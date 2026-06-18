import { defineConfig } from "astro/config";

// 仓库名占位。如最终仓库名不是 portraits，请同步修改。
const REPO = "portraits";

export default defineConfig({
  site: `https://example.github.io/${REPO}/`,
  base: `/${REPO}/`,
  build: {
    assets: "_assets",
  },
});
