import * as d3 from 'd3';

const fixedTypes = ["stigma", "no stigma"];

/**
 * 高亮节点
 * @param {object} d 节点数据
 * @param {object} event D3事件对象
 * @param {d3.Selection} mainGroup 主绘制分组
 * @param {array} highlightedLegendTypes 当前高亮的类型数组
 */
export function highlightNode(d, event, mainGroup, highlightedLegendTypes, thirdElementToInstances) {
  // 1) 计算 occurrence = 该节点下有多少 instance
  let occurrence = 0;
  if (thirdElementToInstances && thirdElementToInstances[d.name]) {
    occurrence = thirdElementToInstances[d.name].length;
  } else  {
    occurrence = d.weight;
  }
  // 2) 显示tooltip
  d3.select("#chart")
    .append("div")
    .attr("class", "tooltip")
    .style("position", "absolute")
    .style("background", "#e0e0e0")
    .style("border", "1px solid #ccc")
    .style("padding", "5px")
    .style("pointer-events", "none")
    .style("font-size", "12px")
    .style("left", `${event.pageX + 5}px`)
    .style("top", `${event.pageY + 5}px`)
    .html(`
      <strong>Name:</strong> ${d.name}<br>
      <strong>Type:</strong> ${d.type}<br>
      <strong>Occurrence:</strong> ${occurrence}
    `);

  // 3) 如果当前已有高亮类型筛选，则不改变透明度
  if (highlightedLegendTypes.length > 0) return;

  // 4) 否则对链接 & 节点 & 标签做透明度处理
  const link = mainGroup.selectAll("path");
  const node = mainGroup.selectAll("circle");
  const labels = mainGroup.selectAll(".node-label");

  const connectedNodes = new Set();
  link.style("stroke-opacity", l => {
    if (l.source === d || l.target === d) {
      connectedNodes.add(l.source);
      connectedNodes.add(l.target);
      return 1;
    }
    return 0.1;
  });

  node.style("opacity", n => connectedNodes.has(n) ? 1 : 0.1);
  labels.style("opacity", n => connectedNodes.has(n) ? 1 : 0.1);
}

/**
 * 重置节点高亮
 * @param {object} d 节点数据
 * @param {d3.Selection} mainGroup 主绘制分组
 * @param {array} highlightedLegendTypes 当前高亮的类型数组
 * @param {function} setShowHighlightStats 用于更新显示高亮信息的回调
 * @param {function} setHighlightedCount 用于更新高亮计数的回调
 */
export function resetHighlightNode(d, mainGroup, highlightedLegendTypes, setShowHighlightStats, setHighlightedCount) {
  // 移除 tooltip
  d3.selectAll(".tooltip").remove();

  // 如果已有高亮类型，不重置
  if (highlightedLegendTypes.length > 0) return;

  const link = mainGroup.selectAll("path");
  const node = mainGroup.selectAll("circle");
  const labels = mainGroup.selectAll(".node-label");

  link.style("stroke-opacity", 1);
  node.style("opacity", 1);
  labels.style("opacity", 1);

  setHighlightedCount(0);
  setShowHighlightStats(false);
}

/**
 * 高亮边
 * @param {object} d 边数据
 * @param {d3.Selection} mainGroup 主绘制分组
 * @param {array} highlightedLegendTypes 当前高亮的类型数组
 */
export function highlightLink(d, mainGroup, highlightedLegendTypes) {
  const link = mainGroup.selectAll("path");
  const node = mainGroup.selectAll("circle");
  const labels = mainGroup.selectAll(".node-label");

  link.style("stroke-opacity", l => {
    /**
     * 这个地方不加下面的判断会报错
     */
    if (!l.source || !l.target) {
      return 0.1; // 如果没有 source 或 target 对象，则无法高亮，返回默认透明度
    }
    const sourceType = l.source.type;
    const targetType = l.target.type;
    if (!sourceType || !targetType) {
      return 0.1;
    }
    
    const isHovered = (l === d);
    const isHighlighted = (highlightedLegendTypes.includes(l.source.type) || fixedTypes.includes(l.source.type)) &&
                          (highlightedLegendTypes.includes(l.target.type) || fixedTypes.includes(l.target.type));
    return isHovered || isHighlighted ? 1 : 0.1;
  });

  node.style("opacity", n => {
    const isConnected = (n === d.source || n === d.target);
    const isHighlightedType = highlightedLegendTypes.includes(n.type) || fixedTypes.includes(n.type);
    return isConnected || isHighlightedType ? 1 : 0.1;
  });

  labels.style("opacity", n => {
    const isConnected = (n === d.source || n === d.target);
    const isHighlightedType = highlightedLegendTypes.includes(n.type) || fixedTypes.includes(n.type);
    return isConnected || isHighlightedType ? 1 : 0.1;
  });
}

/**
 * 重置边高亮
 * @param {object} d 边数据
 * @param {d3.Selection} mainGroup 主绘制分组
 * @param {array} highlightedLegendTypes 当前高亮的类型数组
 * @param {function} setShowHighlightStats 用于更新显示高亮信息的回调
 * @param {function} setHighlightedCount 用于更新高亮计数的回调
 */
export function resetHighlightLink(d, mainGroup, highlightedLegendTypes, setShowHighlightStats, setHighlightedCount) {
  // 如果已有高亮类型，不重置
  if (highlightedLegendTypes.length > 0) return;

  const link = mainGroup.selectAll("path");
  const node = mainGroup.selectAll("circle");
  const labels = mainGroup.selectAll(".node-label");

  link.style("stroke-opacity", 1);
  node.style("opacity", 1);
  labels.style("opacity", 1);

  setHighlightedCount(0);
  setShowHighlightStats(false);
}

/**
 * 根据背景色动态决定文本颜色（黑或白）
 * @param {*} backgroundColor 
 * @returns 
 */
export function getTextColor(backgroundColor) {
  const color = d3.color(backgroundColor);
  const brightness = 0.299 * color.r + 0.587 * color.g + 0.114 * color.b;
  return brightness > 170 ? 'black' : 'white';
}

/**
 * 根据缩放级别来决定哪些标签显示
 * @param {*} zoomLevel 
 */
export function handleZoom(zoomLevel) {
  const smallThreshold = 0.2;
  const mediumThreshold = 0.4;
  const bigThreshold = 5;

  d3.selectAll(".node-label")
    .attr("display", d => {
      if (zoomLevel >= bigThreshold) {
        return "block";
      } else if (zoomLevel >= mediumThreshold && d.size >= 30) {
        return "block";
      } else if (zoomLevel >= smallThreshold && d.size >= 60) {
        return "block";
      } else if (zoomLevel < smallThreshold && d.size >= 100) {
        return "block";
      } else {
        return "none";
      }
    });
}

/**
 * 切换高亮类型
 * @param {*} type 
 * @param {*} highlightedLegendTypes 
 */
export function toggleHighlight(type, highlightedLegendTypes) {
  const index = highlightedLegendTypes.indexOf(type);
  if (index !== -1) {
    highlightedLegendTypes.splice(index, 1);
  } else {
    highlightedLegendTypes.push(type);
  }
}

/**
 * 应用高亮效果
 * @param {*} mainGroup 
 * @param {*} nodes 
 * @param {*} highlightedLegendTypes 
 * @param {*} totalNodeCount 
 * @param {*} setShowHighlightStats 
 * @param {*} setHighlightedCount 
 * @returns 
 */
export function applyHighlight(mainGroup, nodes, highlightedLegendTypes, setShowHighlightStats, setHighlightedCount) {
  const node = mainGroup.selectAll("circle");
  const link = mainGroup.selectAll("path");
  const labels = mainGroup.selectAll(".node-label");

  const fixedTypes = ["stigma", "no stigma"];

  if (highlightedLegendTypes.length === 0) {
    node.style("opacity", 1);
    link.style("stroke-opacity", 1);
    labels.style("opacity", 1);
    setHighlightedCount(0);
    setShowHighlightStats(false);
    return;
  }

  node.style("opacity", d =>
    highlightedLegendTypes.includes(d.type) ||
    fixedTypes.includes(d.type) ? 1 : 0.1
  );

  link.style("stroke-opacity", l =>
    (highlightedLegendTypes.includes(l.source.type) || fixedTypes.includes(l.source.type)) &&
    (highlightedLegendTypes.includes(l.target.type) || fixedTypes.includes(l.target.type)) ? 1 : 0.1
  );

  labels.style("opacity", d =>
    highlightedLegendTypes.includes(d.type) ||
    fixedTypes.includes(d.type) ? 1 : 0.1
  );

  const highlightedCount = nodes.filter(d =>
    highlightedLegendTypes.includes(d.type) ||
    fixedTypes.includes(d.type)
  ).length;

  setHighlightedCount(highlightedCount);
  setShowHighlightStats(true);
}

/**
 * 重置高亮状态
 * @param {*} mainGroup 
 * @param {*} setHighlightedCount 
 * @param {*} setShowHighlightStats 
 */
export function resetHighlight(mainGroup, setHighlightedCount, setShowHighlightStats) {
  const node = mainGroup.selectAll("circle");
  const link = mainGroup.selectAll("path");
  const labels = mainGroup.selectAll(".node-label");

  node.style("opacity", 1);
  link.style("stroke-opacity", 1);
  labels.style("opacity", 1);

  setHighlightedCount(0);
  setShowHighlightStats(false);
}