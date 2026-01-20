import axios from "axios";
import { zoomToNode } from "@/utils/clickUtils";
import config from "@/config";

/**
 * 搜索并高亮匹配的节点
 * @param {Object} context - Vue 组件的上下文
 */
export async function handleSearch(context) {
  if (!context.searchQuery) return;

  try {
    const requestBody = {
      nodes: context.nodes.map(node => node.name), // 仅传递节点名称
      query: context.searchQuery,
    };

    const res = await axios.post(`${config.baseURL}/api/${context.userId}/search/search-with-nodes`, requestBody);
    context.searchResults = res.data; // [{ name, distance }]

    // 自动跳转到最匹配的节点
    if (context.searchResults.length > 0) {
      const bestMatch = context.searchResults[0];
      if (bestMatch.distance === 0) {
        const targetNode = context.nodes.find(n => n.name === bestMatch.name);
        if (targetNode) {
          zoomToNode(context, targetNode, 5); // 直接调用 clickUtils 里的 zoomToNode
        }
      }
    }
  } catch (error) {
    console.error("Search error:", error);
  }
}