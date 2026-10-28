import { ref } from "vue";
import { defineStore } from "pinia";
import { getProvinces } from "../api/chapters";

const THEME_KEY = "sx_theme";
const FONT_KEY = "sx_font";
const PROVINCE_KEY = "sx_province";

const THEMES = ["light", "dark"];
const FONT_SIZES = ["small", "medium", "large"];
const THEME_COLORS = {
  light: "#0E5A4A",
  dark: "#101614",
};

function readStorage(key, fallback = "") {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 忽略隐私模式等场景下的存储异常
  }
}

export const useUiStore = defineStore("ui", () => {
  const savedTheme = readStorage(THEME_KEY, "light");
  const savedFont = readStorage(FONT_KEY, "medium");

  const theme = ref(THEMES.includes(savedTheme) ? savedTheme : "light");
  const fontSize = ref(
    FONT_SIZES.includes(savedFont) ? savedFont : "medium"
  );
  // 游客本地省份；登录用户的真实省份以 auth.user.province_code 为准
  const provinceCode = ref(readStorage(PROVINCE_KEY, "SC"));
  const provinces = ref([]);

  /** 把主题与字体同步到 <html> 与 meta theme-color。 */
  function applyToDocument() {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    root.dataset.theme = theme.value;
    root.dataset.font = fontSize.value;
    root.style.colorScheme = theme.value === "dark" ? "dark" : "light";

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", THEME_COLORS[theme.value] || THEME_COLORS.light);
    }
  }

  function setTheme(value) {
    theme.value = THEMES.includes(value) ? value : "light";
    writeStorage(THEME_KEY, theme.value);
    applyToDocument();
  }

  function toggleTheme() {
    setTheme(theme.value === "dark" ? "light" : "dark");
  }

  function setFontSize(value) {
    fontSize.value = FONT_SIZES.includes(value) ? value : "medium";
    writeStorage(FONT_KEY, fontSize.value);
    applyToDocument();
  }

  function setProvinceCode(code) {
    provinceCode.value = code || "";
    writeStorage(PROVINCE_KEY, provinceCode.value);
  }

  /** 加载并缓存省份列表。 */
  async function loadProvinces(force = false) {
    if (provinces.value.length && !force) return provinces.value;
    const data = await getProvinces();
    provinces.value = Array.isArray(data) ? data : [];
    return provinces.value;
  }

  /** 应用启动时读取本地设置并应用。 */
  function init() {
    const localTheme = readStorage(THEME_KEY, theme.value);
    if (THEMES.includes(localTheme)) theme.value = localTheme;

    const localFont = readStorage(FONT_KEY, fontSize.value);
    if (FONT_SIZES.includes(localFont)) fontSize.value = localFont;

    const localProvince = readStorage(PROVINCE_KEY, provinceCode.value);
    provinceCode.value = localProvince;

    applyToDocument();
  }

  return {
    theme,
    fontSize,
    provinceCode,
    provinces,
    applyToDocument,
    setTheme,
    toggleTheme,
    setFontSize,
    setProvinceCode,
    loadProvinces,
    init,
  };
});
