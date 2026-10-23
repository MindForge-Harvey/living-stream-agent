/**
 * 根据当前浏览器地址自动探测访问前缀。
 *
 * 场景：前端页面部署在 B 服务器，但用户通过 A 域名访问
 * （地址形如 https://a.com/snsst/ChannelApp/chat），
 * 前端里发起的相对请求 /chat/api/** 会发往 A 域名，
 * 因缺少 /snsst/ChannelApp 前缀而无法被 C 服务器转发到 B。
 *
 * 本函数从 window.location.pathname 中探测出该前缀并自动拼接到
 * 所有 API 请求前，保证请求走 A -> C -> B 的转发链路。
 *
 * @returns {string} 访问前缀，若无则返回空字符串
 */
export function apiPrefix() {
  if (typeof window === 'undefined') return ''
  const pathname = window.location.pathname || ''
  const match = pathname.match(/^(\/snsst\/ChannelApp)(?:\/|$)/i)
  return match ? match[1] : ''
}

/**
 * 用于拼接后端 API 路径。传入以 / 开头的绝对路径（如 /chat/api/assistant），
 * 自动加上检测到的访问前缀。
 *
 * @param {string} path API 绝对路径，以 / 开头
 * @returns {string} 带前缀的完整路径
 */
export function apiUrl(path) {
  return apiPrefix() + path
}
