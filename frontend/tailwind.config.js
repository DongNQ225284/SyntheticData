var config = {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                canvas: "#f4f8fd",
                shell: "#fbfdff",
                line: "#dbe7f4",
                brand: "#1d8fff",
                ink: "#111827",
                muted: "#64748b"
            },
            boxShadow: {
                shell: "0 18px 42px rgba(30, 64, 175, 0.10)",
                panel: "0 8px 24px rgba(15, 23, 42, 0.06)"
            },
            borderRadius: {
                xl2: "1.25rem"
            },
            fontFamily: {
                sans: ["Manrope", "\"Segoe UI Variable\"", "\"Avenir Next\"", "\"Segoe UI\"", "sans-serif"]
            }
        }
    },
    plugins: []
};
export default config;
