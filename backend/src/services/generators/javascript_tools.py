"""JavaScript tool code generator."""

from services.generators._models import GeneratedTool


def _generate_javascript_tool(tool_id: str, description: str) -> GeneratedTool:
    desc_lower = description.lower()

    if any(kw in desc_lower for kw in ["读取", "read", "文件", "file"]):
        name = "readFile"
        desc = "读取文件内容"
        code = """const fs = require('fs').promises;

async function readFile(filePath, encoding = 'utf-8') {
    /**
     * 读取文件内容
     * @param {string} filePath - 文件路径
     * @param {string} encoding - 文件编码，默认UTF-8
     * @returns {Promise<string>} 文件内容
     */
    try {
        const content = await fs.readFile(filePath, encoding);
        return content;
    } catch (error) {
        throw new Error(`读取文件失败: ${error.message}`);
    }
}

module.exports = { readFile };
"""
        params = {
            "filePath": {"type": "string", "required": True},
            "encoding": {"type": "string", "default": "utf-8"},
        }

    elif any(kw in desc_lower for kw in ["天气", "weather", "气温", "温度", "forecast"]):
        name = "getWeather"
        desc = "查询城市天气信息"
        code = """async function getWeather(city, apiKey = null) {
    /**
     * 查询指定城市的天气信息（使用 wttr.in 免费接口）
     * @param {string} city - 城市名称（英文），如 "Beijing", "Shanghai"
     * @param {string|null} apiKey - 可选的 OpenWeatherMap API Key
     * @returns {Promise<Object>} 天气信息对象
     */
    try {
        let data;
        if (!apiKey) {
            const resp = await fetch(`https://wttr.in/${city}?format=j1`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            data = await resp.json();
            const current = data.current_condition?.[0] || {};
            return {
                city,
                temperatureC: current.temp_C || '',
                temperatureF: current.temp_F || '',
                description: current.weatherDesc?.[0]?.value || '',
                humidity: current.humidity || '',
                windSpeedKmph: current.windspeedKmph || '',
                windDir: current.winddir16Point || '',
                feelsLikeC: current.FeelsLikeC || '',
                success: true
            };
        } else {
            const resp = await fetch(`https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${apiKey}&units=metric&lang=zh_cn`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            data = await resp.json();
            return {
                city,
                temperatureC: data.main?.temp || '',
                description: data.weather?.[0]?.description || '',
                humidity: data.main?.humidity || '',
                windSpeedMs: data.wind?.speed || '',
                success: true
            };
        }
    } catch (error) {
        return { city, success: false, error: error.message };
    }
}

module.exports = { getWeather };
"""
        params = {
            "city": {"type": "string", "required": True},
            "apiKey": {"type": "string", "required": False},
        }

    else:
        name = "customTool"
        desc = description[:50]
        code = f"""async function customTool(inputData = null) {{
    /**
     * {description}
     * @param {{*}} inputData - 输入数据
     * @returns {{Promise<*>}} 处理结果
     */
    return inputData;
}}

module.exports = {{ customTool }};
"""
        params = {"inputData": {"type": "any", "required": False}}

    return GeneratedTool(
        id=tool_id,
        name=name,
        description=desc,
        code=code,
        language="javascript",
        parameters=params,
        is_valid=True,
    )
