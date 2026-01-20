<template>
  <div v-if="showHighlightStats" class="highlight-stats">
    <p>{{ highlightedCount }} / {{ totalNodeCount }} ({{ (highlightedCount / totalNodeCount * 100).toFixed(2) }}%)</p>
  </div>

  <!-- 错误消息提示框 -->
  <div v-if="Object.keys(validationErrors).length > 0" class="validation-overlay">
    <div class="validation-errors">
      <div v-for="(error, field) in validationErrors" :key="field" class="error-item">
        <p>{{ error }}</p>
      </div>
      <!-- 添加一个关闭按钮（可选） -->
      <button @click="clearValidationErrors" class="close-button">关闭</button>
    </div>
  </div>

  <div class="container">
    <!-- 图例部分 -->
    <div class="legend-wrapper">
      <svg id="legend" class="legend-container"></svg>
    </div>

    <!-- 图表部分 -->
    <div id="chart" class="chart"></div>

    <div class="controls button-group">
      <button @click="undoOperation" class="undo-button" :disabled="undoStack.length === 0">
        Undo
      </button>
      <button @click="navigateToMain" class="nav-button">
        <img src="@/assets/home-icon.svg" alt="Go to Main" class="icon" />
      </button>
      <button @click="saveAllOperations" class="save-button">Save</button>
    </div>

    <transition name="fade">
      <div class="instance-content" v-if="isInstanceContentVisible && selectedInstances.length > 0">

        <!-- 关闭按钮：绝对定位在 Sidebar右上角 -->
        <button 
          class="sidebar-close-button" 
          @click="hideInstanceContent"
        >
          x
        </button>
        
        <div class="node-name-container">
          <template v-if="selectedInstances[currentIndex].editableName">
            <textarea
              id="node-name"
              v-model="selectedInstances[currentIndex].name"
              placeholder="Enter node name"
              class="name-input"
              style="height:40px; font-size:1.5em; font-weight:bold; line-height:1.2;"
            ></textarea>
          </template>
          <!-- <h3 class="node-index-info">({{ currentIndex + 1 }} / {{ selectedInstances.length }})</h3> -->
          <template v-else>
            <h3>{{ selectedNodeName }} ({{ currentIndex + 1 }} / {{ selectedInstances.length }})</h3>
          </template>
        </div>

        <div :class="{'instance-section': true, 'no-bg': isEditMode}">
          <div class="instance-item">
            <!-- 根据 isEditMode 切换展示/编辑 -->
            <div class="detail-row">
              <div class="bullet-title">
                <span class="bullet bullet-category"></span>
                <p class="aligned">
                  <strong>Category:</strong>
                  <template v-if="!isEditMode">
                    {{ selectedInstances[currentIndex].category_ }}
                  </template>
                  <template v-else>
                    <select v-model="selectedInstances[currentIndex].category_" class="edit-input">
                      <option v-for="category in categoryOptions" :key="category" :value="category">
                        {{ category }}
                      </option>
                    </select>
                  </template>
                </p>
              </div>
            </div>
            <div class="detail-row">
              <div class="bullet-title">
                <span class="bullet bullet-attribution"></span>
                <p class="aligned">
                  <strong>Attribution:</strong>
                  <template v-if="!isEditMode">
                    {{ selectedInstances[currentIndex].attribution_type_ }}
                  </template>
                  <template v-else>
                    <select v-model="selectedInstances[currentIndex].attribution_type_" class="edit-input">
                      <option v-for="attribution in attributionOptions" :key="attribution" :value="attribution">
                        {{ attribution }}
                      </option>
                    </select>
                  </template>
                </p>
              </div>
            </div>
            <div class="detail-row">
              <div class="bullet-title">
                <span class="bullet bullet-type"></span>
                <p class="aligned">
                  <strong>Type:</strong>
                  <template v-if="!isEditMode">
                    {{ selectedInstances[currentIndex].type }}
                  </template>
                  <template v-else>
                    <select v-model="selectedInstances[currentIndex].type" class="edit-input">
                      <option v-for="type in typeOptions" :key="type" :value="type">
                        {{ type }}
                      </option>
                    </select>
                  </template>
                </p>
              </div>
            </div>
            <div class="detail-row">
              <div class="bullet-title">
                <span class="bullet bullet-interviewer"></span>
                <p>
                  <strong>Interviewer: </strong>
                  <template v-if="!isEditMode">
                    {{ selectedInstances[currentIndex].question }}
                  </template>
                  <template v-else>
                    <!-- 大容器，用于显示文本、边框，与 Participant 宽度一致 -->
                    <div 
                      class="interviewer-container" 
                      @mouseover="showArrows = true" 
                      @mouseleave="showArrows = false"
                    >
                      <!-- 左箭头（只在 showArrows 为 true 时显示） -->
                      <button 
                        class="arrow-button arrow-left" 
                        v-if="showArrows" 
                        @click="prevInterview" 
                        :disabled="currentSlideIndex === 0"
                      >
                        <img 
                          src="@/assets/previous.svg" 
                          alt="Previous" 
                          class="arrow-icon"
                        />
                      </button>

                      <!-- 中间的文本区域 -->
                      <div class="interviewer-text">
                        {{ displayedInterview }}
                      </div>

                      <!-- 右箭头（只在 showArrows 为 true 时显示） -->
                      <button 
                        class="arrow-button arrow-right" 
                        v-if="showArrows" 
                        @click="nextInterview" 
                        :disabled="currentSlideIndex === interviewOptions.length - 1"
                      >
                        <img 
                          src="@/assets/next.svg" 
                          alt="Next" 
                          class="arrow-icon"
                        />
                      </button>
                    </div>

                    <!-- 下方 7 个点（与 interviewOptions.length 对应） -->
                    <div class="dots-container">
                      <span 
                        v-for="(option, index) in interviewOptions" 
                        :key="index"
                        class="dot"
                        :class="{ active: index === currentSlideIndex }"
                        @click="jumpToInterview(index)"
                      ></span>
                    </div>
                  </template>
                </p>
              </div>
            </div>
            <div class="detail-row">
              <div class="bullet-title">
                <span class="bullet bullet-participant"></span>
                <p>
                  <strong>Participant: </strong>
                  <template v-if="!isEditMode">
                    {{ selectedInstances[currentIndex].opinion }}
                  </template>
                  <template v-else>
                    <textarea 
                      v-model="selectedInstances[currentIndex].opinion" 
                      class="edit-input" 
                      style="height:100px; font-size: 16px; line-height: 1.2; font-weight: normal; color: #333; font-family: 'Arial', sans-serif;">
                    </textarea>
                  </template>
                </p>
              </div>
            </div>
          </div>

          <div class="button-container">
            <button @click="EditInstance" class="edit-button" v-if="!isEditMode">Edit</button>
            <button @click="addNewInstance" class="add-button" v-if="!isEditMode">Add</button>
            <button @click="deleteInstance(currentIndex)" class="delete-button" v-if="!isEditMode">Delete</button>
          </div>

          <!-- 如果处于编辑模式，显示保存 / 取消 -->
          <div class="edit-actions" v-if="isEditMode">
            <button 
              @click="isNodeEditMode ? saveCurrentNode() : saveCurrentInstance()"
              style="margin-right: 10px;"
            >
              Save
            </button>
            <button @click="cancelEdit">Cancel</button>
          </div>
        </div>

        <div class="pagination">
          <button @click="prevInstance" :disabled="currentIndex === 0">
            <img src="@/assets/previous.svg" alt="Previous" class="icon" />
          </button>
          <button @click="goToNodeView" class="jump-button">
            <img src="@/assets/layer.svg" alt="Previous" class="icon" />
          </button>
          <button @click="nextInstance" :disabled="currentIndex === selectedInstances.length - 1">
            <img src="@/assets/next.svg" alt="Next" class="icon" />
          </button>
          <button @click="hideInstanceContent" class="sidebar-close-button">x</button>
        </div>

      </div>
    </transition>
  </div>

  <div class="zoom-container">
    <div class="zoom-controls">
      <input
        type="range"
        min="10"
        max="1000"
        v-model="zoomPercent"
        @input="updateZoom"
      />
      <span>{{ zoomPercent }}%</span>
    </div>
  </div>

</template>

<script>
import * as d3 from 'd3';
import axios from 'axios';
import config from "@/config";
import '@/assets/styles/common.css';
import { handleNodeClick } from '@/utils/clickUtils';
import { dragStarted, dragged, dragEnded } from '@/utils/dragUtils.js';
import { highlightNode, resetHighlightNode, highlightLink, resetHighlightLink, getTextColor, handleZoom, toggleHighlight, applyHighlight, resetHighlight } from '@/utils/graphUtils.js';
import { addNewNode, saveCurrentNode, deleteNode } from "@/utils/nodeUtils";
import { EditInstance, addNewInstance, saveCurrentInstance, deleteInstance } from "@/utils/instanceUtils"
import { cancelEdit, undoOperation, saveAllOperations, showInstanceContent, blockIfPendingNewNode } from '@/utils/operationUtils.js';
import { prevInterview, nextInterview, updateQuestion} from '@/utils/templateUtils.js';
// import { restoreUserState } from '@/utils/replayUtils.js';

export default {
  name: 'NodeView',
  data() {
    return {
      userId: '', // 传入的userId
      name: null, // 传入的节点名
      sourceName: null, // 源节点名
      nodes: [],  // 点集合
      links: [],  // 边集合
      thirdElementToInstances: {}, // 实例集合
      svg: null,
      zoom: null, // 缩放模块
      zoomPercent: 40,  // 缩放比例
      width: 0,
      height: 0,
      initialX: 0,  // 初始X坐标 
      initialY: 0,  // 初始Y坐标
      initialPositions: {}, // 点的初始位置
      selectedNodeName: '',
      selectedInstances: [],
      currentIndex: 0,
      simulation: null,
      mainGroup: null, 
      isInstanceContentVisible: false,
      highlightedLegendTypes: [],
      highlightedCount: 0,
      totalNodeCount: 0,
      showHighlightStats: false,
      originalInstances: [],  // 用于保存进入编辑模式前的原始数据副本
      isEditMode: false,  // 是否为 instance 编辑模式
      isNodeEditMode: false, // 是否为 node 编辑模式
      undoStack: [], // 用于存放删除前的状态
      categoryOptions: ["stigma", "no stigma"], // 下拉框选择
      attributionOptions: [
        "responsibility",
        "fear and dangerousness",
        "anger",
        "no pity",
        "social distance",
        "no help",
        "coercion segregation",
        "no responsibility",
        "no fear and dangerousness",
        "no anger",
        "pity",
        "help",
        "no social distance",
        "no coercion segregation",
      ], 
      typeOptions: [
        "cognitive judgment",
        "signaling event",
        "personality",
        "suggestion",
        "belief",
        "feeling",
        "situation",
        "past experience",
        "potential outcome",
        "behavior",
        "motivation",
      ],
      interviewOptions: [
        "Just like what is mentioned in the story, Avery is currently facing difficulties in both their relationships with colleagues and their work performance. Do you believe Avery’s current situation is primarily a result of their actions? Please share your thoughts.",
        "If you were in the process of selecting a tenant for your home, would you feel comfortable entrusting it to someone like Avery?",
        "Let’s imagine you were one of Avery’s friends at the party or other social occasions. Would you feel anger toward them due to their actions, for example, losing their temper and yelling at someone?",
        "I wonder if you were one of Avery’s colleagues or friends, then would you be inclined to help them with tasks, such as work projects?",
        "I’d like to know if you would feel concern and sympathy at Avery’s mental state?",
        "Apart from being a colleague or friend, I’m also curious if you are Avery’s neighbor, then would you consider it better to separate them from the neighborhood and have them undergo hospitalization for treatment?",
        "If you were traveling or engaging in activities with Avery, would you have any feelings of frightened or being threatened regarding the potential implications of your interaction?",
      ],
      currentSlideIndex: 0,
      userOperations: [],
      isCreateNewNode: false,
      validationErrors: {},
      isDirty: true,
      showArrows: false,
    };
  },

  computed: {
    displayedInterview() {
      // 只要确保 currentSlideIndex 在有效范围内
      return this.interviewOptions[this.currentSlideIndex] || "";
    }
  },

  beforeRouteUpdate(to, from, next) {
    if (to.query.id !== from.query.id) {
      console.log("changing...")
      this.name = to.query.id;
      this.mainGroup.selectAll("*").remove(); // 清除旧的 D3 图
      this.fetchGraphData(); // 重新加载数据
    }
    next();
  },


  async mounted() {
    this.userOperations = [];
    this.name = this.$route.query.id;               // 获取传递的节点名称
    this.userId = this.$route.query.userId;         // 获取传递的 userId
    this.sourceName = this.$route.query.sourceName; 
    this.initializeVisualization();                 // 初始化可视化设置
    await this.fetchGraphData();                    // 从后端获取数据

    // try {
    //   const response = await axios.get(`${config.baseURL}/api/operations/${this.userId}`);
    //   const userOperations = response.data;
    //   this.isCreateNewNode = restoreUserState(userOperations, this.thirdElementToInstances, this.nodes, this.links);

    //   // 有新node创建操纵时才重新处理数据，为了避免中间数据被重新处理
    //   if (this.isCreateNewNode) {
    //     this.processData(this.thirdElementToInstances, this.nodes, this.links);
    //     this.isCreateNewNode = false; // 重置标志
    //   }

    // } catch (error) {
    //   console.error("Error fetching user operations:", error);
    // }

    this.mainGroup.selectAll("*").remove(); // 重放操作后重新渲染图形
    this.renderGraph();

    window.addEventListener("beforeunload", (event) => {
      // 如果还有未保存的操作 => 拦截刷新
      if (this.isDirty) {
        event.preventDefault();
        // 设置 returnValue
        event.returnValue = "You have unsaved changes. Are you sure you want to leave?";
      }
    });
  },

  methods: {
    pauseSimulation() {
      if (this.simulation) {
        this.simulation.alphaTarget(0); // 停止模拟
        this.simulation.stop();        // 完全停止
      }
    },

    resumeSimulation() {
      if (this.simulation) {
        this.simulation.restart(); // 重新启动模拟
      }
    },

    fixNodePosition(node) {
      node.fx = node.x; // 固定节点的 x 坐标
      node.fy = node.y; // 固定节点的 y 坐标
    },

    releaseNodePosition(node) {
      node.fx = null; // 释放节点的 x 坐标
      node.fy = null; // 释放节点的 y 坐标
    },

    initializeVisualization() {
      const width = window.innerWidth;
      const height = window.innerHeight;
      this.width = width;
      this.height = height;

      const initialScale = 0.4;
      this.initialX = width / 5.5;
      this.initialY = height / 5;

      const mainColors = {
        'stigma':'#ffaebc',
        'no stigma': '#94C973'
      };

      const typeToColorMap = {
        'cognitive judgment': '#F37970',
        'signaling event': '#FFD93D',
        'personality': '#6BCB77',
        'suggestion': '#4D96FF',
        'belief': '#C26DBC',
        'feeling': '#FF9770',   
        'situation': '#FFCD94',
        'past experience': '#75B79E',
        'potential outcome': '#FFC7C7',    
        'behavior': '#95D5B2',   
        'motivation': '#BFD7ED'            
      };

      const svg = d3.select("#chart")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

      this.svg = svg; 
      this.mainGroup = svg.append("g");

      this.zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on("zoom", (event) => {
          this.mainGroup.attr("transform", event.transform);
          this.zoomPercent = Math.round(event.transform.k * 100);
          this.handleZoom(event.transform.k);
        });

      svg.call(this.zoom);
      svg.call(this.zoom.transform, d3.zoomIdentity.translate(this.initialX, this.initialY).scale(initialScale));

      const legendSvg = d3.select("#legend")
        .attr("width", 100)
        .attr("height", height);

      const legend = legendSvg.append("g")
        .attr("transform", "translate(10, 20)");

      const legendData = Object.assign({}, mainColors, typeToColorMap);

      const legendItems = legend.selectAll(".legend-item")  // 图例
        .data(Object.keys(legendData))
        .enter()
        .append("g")
        .attr("class", "legend-item")
        .attr("transform", (d, i) => `translate(0, ${i * 20})`)
        .on("click", (event, d) => this.toggleHighlight(d));

      legendItems.append("rect")  // 图例方块
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", 15)
        .attr("height", 15)
        .attr("fill", d => legendData[d]);

      legendItems.append("text")  // 图例文字
        .attr("x", 20)
        .attr("y", 12)
        .attr("font-size", "12px")
        .text(d => d);
    },

    handleZoom(zoomLevel) {
      handleZoom(zoomLevel);
    },

    async fetchGraphData() {
      try {
        const stigmaTypes = [
          'responsibility',
          'fear and dangerousness',
          'anger',
          'no pity',
          'social distance',
          'no help',
          'coercion segregation'
        ];
        // 1. 获取当前节点信息
        const nodeResponse = await axios.get(`${config.baseURL}/api/${this.userId}/nodes/name/${this.name}`);
        const currentNode = nodeResponse.data;
        // 2. 其他数据，比如 instances
        const instancesResponse = await axios.get(`${config.baseURL}/api/${this.userId}/instance/third-element-to-instances`);
        const instances = instancesResponse.data;
        // 3. 用来去重和存储最终结果
        const visitedNodes = new Map(); // key: nodeName, value: nodeData
        const visitedLinks = new Map(); // key: linkId,   value: linkData
        // 4. BFS 队列初始化
        let queue = [ currentNode ];
        visitedNodes.set(currentNode.name, currentNode);

        let depth = 0;
        const MAX_DEPTH = 10;
        // 5. BFS 循环：从下往上查找 source
        while (queue.length > 0 && depth < MAX_DEPTH) {
          const currentLevelNodes = [...queue];
          queue = [];
          // 对此层的每个节点，查找“谁把它当 target”
          const fetchParents = currentLevelNodes.map(async childNode => {
            if (childNode.name === 'stigma' || childNode.name === 'no stigma') {
              return [];
            }
            const linksRes = await axios.get(`${config.baseURL}/api/${this.userId}/links/target/${childNode.name}`);
            const parentLinks = linksRes.data; // 数组

            const parents = [];
            for (let l of parentLinks) {
              if (!visitedLinks.has(l.id)) {
                visitedLinks.set(l.id, l);
              }
              // 拉取 source 对应的 node
              if (l.source) {
                const parentNodeRes = await axios.get(`${config.baseURL}/api/${this.userId}/nodes/name/${l.source.name}`);
                const parentNode = parentNodeRes.data;
                parents.push(parentNode);
              }
            }
            return parents;
          });

          // 6. 等待所有节点的父节点请求完成
          const results = await Promise.all(fetchParents);
          // 7. 把所有父节点汇总起来
          const allParents = results.flat(); // 把二维数组摊平
          // 8. 逐一处理父节点，检查是否已访问/是否到达顶部
          for (let pNode of allParents) {
            // 如果已经访问过，就不再处理
            if (visitedNodes.has(pNode.name)) {
              continue;
            }

            visitedNodes.set(pNode.name, pNode);
            queue.push(pNode);
            if (
              pNode.name === 'stigma' ||
              pNode.name === 'no stigma' ||
              stigmaTypes.includes(pNode.name)
            ) {
              // 如果你要再补充特殊逻辑，可在这里处理
              // 例如：将其标记为终止节点
            }
          }
          depth++;
        }

        // 9. 把所有收集到的节点、链接做成数组
        const allNodes = Array.from(visitedNodes.values());
        const allLinks = Array.from(visitedLinks.values());

        // 10. 调用后续处理
        this.processData(instances, allNodes, allLinks);

      } catch (error) {
        console.error("Error fetching graph data:", error);
      }
    },

    processData(instances, nodesData, linksData) {

      const sizes = nodesData.map(node => node.size || 1);
      const distances = linksData.map(link => link.distance || 1);

      const sizeScale = d3.scaleSqrt()
          .domain([d3.min(sizes), d3.max(sizes)])
          .range([50, 100]);

      const distanceScale = d3.scaleSqrt()
          .domain([d3.min(distances), d3.max(distances)])
          .range([300, 600]);
      
      // console.log(nodesData)
      this.nodes = nodesData.map(node => ({
        ...node,
        size: sizeScale(node.size),
        color: node.color || '#cccccc',
        x: node.x || Math.random() * window.innerWidth, // 设置随机初始X坐标
        y: node.y || Math.random() * window.innerHeight // 设置随机初始Y坐标
      }));

      // 创建节点映射表，方便通过 name 或 id 快速找到节点对象
      const nodeMap = new Map(this.nodes.map(node => [node.name, node])); // 使用节点的 name 作为键

      this.links = linksData.map(link => {
        const sourceNode = nodeMap.get(link.source.name || link.source); // 查找 source 对应的节点对象
        const targetNode = nodeMap.get(link.target.name || link.target); // 查找 target 对应的节点对象

        if (!sourceNode || !targetNode) {
          // console.warn("Missing source or target for link:", link);
          return null; // 如果找不到 source 或 target，则跳过此链接
        }

        return {
          ...link,
          source: sourceNode, // 替换为完整的节点对象
          target: targetNode, // 替换为完整的节点对象
          color: link.color || '#999999',
          distance: distanceScale(link.distance),
          value: link.value,
        };
      }).filter(link => link !== null); // 过滤掉无效的链接

      // console.log("Links:", this.links);

      this.thirdElementToInstances = instances;
      this.totalNodeCount = this.nodes.length;

      // 渲染图形
      this.renderGraph();
    },

    renderGraph() {
      const width = window.innerWidth;
      const height = window.innerHeight;

      // 初始化 D3 力导向图
      this.simulation = d3.forceSimulation(this.nodes)
        .force("link", d3.forceLink(this.links).id(d => d.name).distance(d => d.distance))
        .force("charge", d3.forceManyBody().strength(0))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => d.size + 20))
        .alpha(1).restart()
        .alphaDecay(0.05)
        .on("tick", () => this.ticked());

      this.updateGraph();
    },

    updateGraph() {
      // 边
      const link = this.mainGroup.append("g")
        .selectAll("path")
        .data(this.links)
        .enter().append("path")
        .attr("fill", "none")
        .attr("stroke-width", d => Math.sqrt(d.value))
        .attr("stroke", d => d.color)
        .on("mouseover", (event, d) => this.highlightLink(d))
        .on("mouseout", (event, d) => this.resetHighlightLink(d));

      link.append("title")
        .text(d => `Weight: ${d.value}, ${d.target.name} because ${d.source.name}`);

      // 节点
      const node = this.mainGroup.append("g")
        .selectAll("circle")
        .data(this.nodes)
        .enter().append("circle")
        .attr("r", d => d.size)
        .attr("fill", d => d.color)
        .attr("data-name", d => d.name)
        .attr("cx", d => this.initialPositions[d.name]?.x || Math.random() * window.innerWidth)
        .attr("cy", d => this.initialPositions[d.name]?.y || Math.random() * window.innerHeight)
        .attr("stroke", d => d3.color(d.color).darker(1))
        .call(d3.drag().filter((event, d) => !d.isThirdElement)
          .on("start", (event, d) => dragStarted(event, d, this.simulation))
          .on("drag", (event, d) => {
            clearTimeout(this.dragTimeout);
            dragged.call(this, event, d); 
          })
          .on("end", (event, d) => dragEnded(event, d, this.simulation))
        )
        .on("click", (event, d) => { this.onNodeClick(event, d) })
        .on("mouseover", (event, d) => this.highlightNode(d))
        .on("mouseout", (event, d) => this.resetHighlightNode(d));

      // 标签
      const labels = this.mainGroup.append("g")
        .selectAll("foreignObject")
        .data(this.nodes)
        .enter().append("foreignObject")
        .attr("class", "node-label")
        .attr("width", d => d.size * 3)
        .attr("height", d => d.size * 3)
        .attr("display", d => d.isThirdElement ? "none" : "block")
        .attr("font-size", d => d.size === 10 ? `3px` : `${Math.max(d.size / 3, 10)}px`)
        .style("pointer-events", "none")
        .append("xhtml:div")
        .style("word-wrap", "break-word")
        .style("white-space", "normal")
        .style("text-align", "center")
        .style("display", "flex")
        .style("align-items", "center")
        .style("justify-content", "center")
        .style("height", "100%")
        .append("div")
        .style("background-color", d => {
          const color = d3.color(d.color);
          return d3.rgb(color.r + 40, color.g + 40, color.b + 40, 0.8);
        })
        .style("color", d => this.getTextColor(d.color))
        .style("border", d => `1px solid ${d3.color(d.color).darker(1)}`)
        .style("padding", "2px 4px")
        .text(d => d.name);

      this.simulation
        .nodes(this.nodes)
        .on("tick", () => this.ticked(link, node, labels));

      this.simulation.force("link")
        .links(this.links);
    },

    updateZoom() {
      const scale = this.zoomPercent / 100;
      if (this.zoom && d3.select("#chart svg")) {
        const transform = d3.zoomIdentity.translate(this.initialX, this.initialY).scale(scale);
        d3.select("#chart svg").transition().duration(200).call(this.zoom.transform, transform);
      } else {
        console.error("Zoom or SVG transform is not initialized");
      }
    },

    getTextColor(backgroundColor) {
      return getTextColor(backgroundColor);
    },

    highlightNode(d) {
      highlightNode(d, event, this.mainGroup, this.highlightedLegendTypes, this.thirdElementToInstances);
    },

    resetHighlightNode(d) {
      resetHighlightNode(d, this.mainGroup, this.highlightedLegendTypes, 
        val => this.showHighlightStats = val, 
        count => this.highlightedCount = count
      );
    },

    highlightLink(d) {
      highlightLink(d, this.mainGroup, this.highlightedLegendTypes);
    },

    resetHighlightLink(d,) {
      resetHighlightLink(d, this.mainGroup, this.highlightedLegendTypes, 
        val => this.showHighlightStats = val, 
        count => this.highlightedCount = count
      );
    },
    
    ticked() {
      // 更新边的位置
      this.mainGroup.selectAll("path")
        .attr("d", d => {
          if (!d.source || !d.target || isNaN(d.source.x) || isNaN(d.source.y) || isNaN(d.target.x) || isNaN(d.target.y)) {
            // console.warn("Invalid link position:", d);
            return ""; // 返回空路径，避免出错
          }

          // 定义控制点生成二次贝塞尔曲线
          const midX = (d.source.x + d.target.x) / 2;
          const midY = (d.source.y + d.target.y) / 2 - 100; // 控制点上下偏移
          return `M ${d.source.x} ${d.source.y} Q ${midX} ${midY} ${d.target.x} ${d.target.y}`;
        });

      // 更新节点的位置
      this.mainGroup.selectAll("circle")
        .attr("cx", d => isNaN(d.x) ? 0 : d.x) // 如果 x 无效，返回默认值 0
        .attr("cy", d => isNaN(d.y) ? 0 : d.y); // 如果 y 无效，返回默认值 0

      // 更新标签的位置
      this.mainGroup.selectAll(".node-label")
        .data(this.nodes)
        .attr("x", d => isNaN(d.x) ? 0 : d.x - d.size * 1.5)
        .attr("y", d => isNaN(d.y) ? 0 : d.y - d.size * 1.5);

      const nodePositions = this.nodes.map(node => ({ name: node.name, x: node.x, y: node.y }));
      localStorage.setItem('nodePositions', JSON.stringify(nodePositions));
    },

    prevInstance() {
      if (this.currentIndex > 0) this.currentIndex--;
    },
    
    nextInstance() {
      if (this.currentIndex < this.selectedInstances.length - 1) this.currentIndex++;
    },

    jumpToInterview(index) {
      this.currentSlideIndex = index;
    },

    goToNodeView() {
      const currentNodeName = this.selectedNodeName || (this.selectedInstances[this.currentIndex] && this.selectedInstances[this.currentIndex].name);

      if (currentNodeName) {
        this.$router.push({
          name: 'NodeView',
          query: {
            userId: this.userId, // 传入的 userId
            id: currentNodeName,
          }
        });
      } else {
        console.error('Node name or additional name is not available for navigation');
      }
    },

    onNodeClick(event, d) {
      if (blockIfPendingNewNode(this)) {
        return; // 阻止切换节点的操作
      }
      handleNodeClick(this, event, d);
    },

    cancelEdit() {
      this.isInstanceContentVisible = false;
      cancelEdit(this);
    },

    EditInstance() {
      EditInstance(this);
    },

    addNewInstance() {
      addNewInstance(this);
    },

    async saveCurrentInstance() {
      await saveCurrentInstance(this);
    },

    deleteInstance(index) {
      deleteInstance(this, index);
    },

    addNewNode() {
      addNewNode(this);
    },

    async saveCurrentNode() {
      await saveCurrentNode(this);
    },

    deleteNode(nodeName) {
      deleteNode(this, nodeName);
    },

    undoOperation() {
      undoOperation(this);
    },

    async saveAllOperations() {
      await saveAllOperations(this, axios, config);
    },

    showInstanceContent() {
      showInstanceContent();
    },

    hideInstanceContent() {
      this.isInstanceContentVisible = false;
      cancelEdit(this);
    },

    toggleHighlight(type) {
      toggleHighlight(type, this.highlightedLegendTypes);
      this.applyHighlight();
    },

    applyHighlight() {
      applyHighlight(this.mainGroup, this.nodes, this.highlightedLegendTypes, (val) => this.showHighlightStats = val, (count) => this.highlightedCount = count);
    },

    resetHighlight() {
      resetHighlight(this.mainGroup, (count) => this.highlightedCount = count, (val) => this.showHighlightStats = val);
    },

    clearValidationErrors() {
      this.validationErrors = {};
    },

    prevInterview() {
      prevInterview(this);
    },

    nextInterview() {
      nextInterview(this);
    },

    updateQuestion() {
      updateQuestion();
    }
  }
}

</script>

<style scoped>

</style>