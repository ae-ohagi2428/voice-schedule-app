module.exports = {
    content: [
        '../templates/**/*.html',
        '../../templates/**/*.html',
        '../../**/templates/**/*.html',
    ],
    theme: {
    extend: {
      colors: {
        // 地色・面
        base:    "#FBF5FA",  // 画面の地色
        surface: "#FFFFFF",  // カード
        line:    "#E2DAEE",  // 枠線（入力欄など）
        hairline:"#F1ECF7",  // 区切り線（リスト内）

        // 文字（濃い順）
        ink:      "#4E4666",  // 見出し
        body:     "#5B5373",  // 本文・タスク名
        muted:    "#8C86A0",  // 補助
        faint:    "#A8A2B8",  // フッター
        fainter:  "#BDB8C9",  // バージョン表記

        // 主役の紫
        brand: {
          DEFAULT: "#9B86C9",  // ヘッダー左・バッジ・トグルON
          deep:    "#6B5B93",  // 主ボタン
          link:    "#7E68B4",  // テキストリンク・強調
          soft:    "#B9A6DE",  // カード枠線（いま）
          pale:    "#EFE9F8",  // プログレスバーの溝
          tint:    "#F3EEF9",  // ごく薄い面
        },
        rose: {
          DEFAULT: "#C8A0C2",  // ヘッダー右
          mark:    "#C0708F",  // 変更マーク（ずれた時刻）
          pale:    "#F3E4EE",  // キャラ枠の下地
        },
        // きゅうけい（水色系）
        rest: {
          bg:   "#E6F0F8",
          ink:  "#4F6478",
          sub:  "#7C90A3",
        },
      },
      fontFamily: {
        // 見出し・ボタン
        maru: ['"Zen Maru Gothic"', '"Hiragino Maru Gothic ProN"', "system-ui", "sans-serif"],
        // 本文・ラベル
        kaku: ['"Zen Kaku Gothic New"', "system-ui", "sans-serif"],
        // 時刻・残り時間（等幅：桁が揃う）
        num:  ["ui-monospace", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "20px",
        pill: "99px",
        sheet: "30px",
      },
      backgroundImage: {
        // ヘッダー
        header: "linear-gradient(135deg, #9B86C9, #C8A0C2)",
        // ログイン前の上部帯（縦寄りの角度）
        "header-tall": "linear-gradient(160deg, #9B86C9, #C8A0C2)",
        // キャラの居場所
        charzone: "linear-gradient(170deg, #F3E4EE, #E9E2F7 55%, #E4EFF8)",
        // プログレスバー
        progress: "linear-gradient(90deg, #9B86C9, #C8A0C2)",
        // 丸い音声ボタン
        mic: "linear-gradient(145deg, #C8A0C2, #9B86C9)",
      },
      boxShadow: {
        card: "0 4px 16px rgba(91,83,115,.07)",
        now: "0 6px 18px rgba(142,123,192,.18)",
        btn: "0 8px 20px rgba(107,91,147,.28)",
        mic: "0 8px 20px rgba(142,123,192,.40)",
        bubble: "0 4px 12px rgba(91,83,115,.12)",
      },
      keyframes: {
        brea: {
          "0%,100%": { transform: "scale(1)", opacity: ".75" },
          "50%":     { transform: "scale(1.06)", opacity: "1" },
        },
      },
      animation: {
        brea: "brea 6s ease-in-out infinite",
      },
    },
  },
    plugins: [
    ],
}