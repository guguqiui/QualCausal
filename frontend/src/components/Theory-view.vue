<template>
  <div class="d3-container">
    <!-- 通过 ref 获取 SVG 节点 -->
    <svg ref="svg"></svg>
  </div>
</template>

<script>
import * as d3 from "d3";
import config from "@/config";

export default {
  name: "AggregationGraph",
  data() {
    return {
      userId: "123", // 替换为真实的用户ID
      apiUrl: "",
      colorMap: {
        "cognitive judgment": "#F37970",
        "signaling event": "#FFD93D",
        "personality": "#6BCB77",
        "suggestion": "#4D96FF",
        "belief": "#C26DBC",
        "feeling": "#FF9770",
        "situation": "#FFCD94",
        "past experience": "#75B79E",
        "potential outcome": "#FFC7C7",
        "behavior": "#95D5B2",
        "motivation": "#BFD7ED"
      }
    };
  },
  mounted() {
    this.fetchData();
  },
  methods: {
    fetchData() {
      this.apiUrl = `${config.baseURL}/api/${this.userId}/nodes/`;
      fetch(this.apiUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error("获取后端数据失败：" + response.statusText);
          }
          return response.json();
        })
        .then(nodeData => {
          // nodeData 应为数组，每个元素包含：id, name, type, weight, size, color, ...
          this.renderGraph(nodeData);
        })
        .catch(err => {
          console.error("数据处理异常:", err);
        });
    },
    renderGraph(nodeData) {
      const validNodesData = nodeData.filter(node => {
        if (!node.type) return false;
        const normalizedType = node.type.trim().toLowerCase();
        return Object.hasOwn(this.colorMap, normalizedType);
      });
      // 1. 根据 nodeData 按 type 聚合生成类型节点
      console.log(validNodesData)
      const typeNodesMap = {};
      validNodesData.forEach(node => {
        if (!typeNodesMap[node.type]) {
          typeNodesMap[node.type] = {
            id: node.type,             // 唯一标识
            label: node.type,          // 显示名称
            color: this.colorMap[node.type] || "#ccc" // 默认颜色
          };
        }
      });
      const typeNodes = Object.values(typeNodesMap);
      console.log(typeNodes)
      // 2. 计算类型之间的连线（累加权重）
      // 遍历所有 nodeData 的组合，若类型不同则累加权重
      const typeEdges = {};
      for (let i = 0; i < validNodesData.length; i++) {
        for (let j = i + 1; j < validNodesData.length; j++) {
          const typeA = validNodesData[i].type;
          const typeB = validNodesData[j].type;
          if (typeA === typeB) continue;
          // 排序后拼接，确保 A-B 与 B-A 为同一条边
          const sortedTypes = [typeA, typeB].sort();
          const edgeKey = sortedTypes.join("-");
          // 此处示例将两个节点的 weight 相加作为当前权重
          const currentWeight = validNodesData[i].weight + validNodesData[j].weight;
          if (!typeEdges[edgeKey]) {
            typeEdges[edgeKey] = {
              source: sortedTypes[0],
              target: sortedTypes[1],
              weight: currentWeight
            };
          } else {
            typeEdges[edgeKey].weight += currentWeight;
          }
        }
      }
      const links = Object.values(typeEdges);

      const minWeight = d3.min(links, d => d.weight);
      const maxWeight = d3.max(links, d => d.weight);
      const strokeScale = d3.scaleLinear()
        .domain([minWeight, maxWeight])
        .range([1, 5]);

      // 3. 绘制力导向图
      const width = window.innerWidth;
      const height = window.innerHeight;

      // 使用 ref 获取 SVG 节点，并设置宽高
      const svgElement = this.$refs.svg;
      const svg = d3.select(svgElement)
        .attr("width", width)
        .attr("height", height);

      // 初始化力模拟
      const simulation = d3.forceSimulation(typeNodes)
        .force("link", d3.forceLink(links)
          .id(d => d.id)
          .distance(150)
        )
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

      // 绘制边
      const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke-width", d => strokeScale(d.weight))
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6);

      // 绘制节点
      const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(typeNodes)
        .enter()
        .append("circle")
        .attr("r", 20)
        .attr("fill", d => d.color)
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended)
        );

      // 添加节点标签
      const label = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(typeNodes)
        .enter()
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dy", ".35em")
        .text(d => d.label);

      simulation.on("tick", () => {
        link
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);

        node
          .attr("cx", d => d.x)
          .attr("cy", d => d.y);

        label
          .attr("x", d => d.x)
          .attr("y", d => d.y);
      });

      // 拖拽事件函数
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }
      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }
      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    }
  }
};
</script>

<style scoped>
.d3-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
}
svg {
  border: 1px solid #ccc;
}
.links line {
  /* 可根据需要调整连线样式 */
}
.nodes circle {
  stroke: #fff;
  stroke-width: 1.5px;
  cursor: grab;
}
.nodes circle:active {
  cursor: grabbing;
}
.labels {
  font-family: sans-serif;
  font-size: 12px;
  pointer-events: none;
}
</style>