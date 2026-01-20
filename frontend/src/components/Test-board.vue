<template>
  <div class="fabric-demo">
    <!-- 说明文字 -->
    <p class="instruction">
      🤓 Please upload your theoretical framework. In the visualization, circles represent factors and edges represent pathways between these factors.
    </p>
    <div class="main-container">
      <!-- 左侧工具栏 -->
      <div class="toolbar-container">
        <button @click="addRect">Add Rectangle (with text)</button>
        <button @click="addCircle">Add Circle (with text)</button>

        <hr/>

        <!-- 选择箭头的起点和终点 -->
        <select v-model="arrowFromIndex">
          <option v-for="(group, idx) in shapeGroups" :key="idx" :value="idx">
            {{ group.textLabel }}
          </option>
        </select>
        <select v-model="arrowToIndex">
          <option v-for="(group, idx) in shapeGroups" :key="idx" :value="idx">
            {{ group.textLabel }}
          </option>
        </select>
        <button @click="addArrow">Add Arrow</button>
        <div class="small-info">先选“起始形状”和“目标形状”，再点“Add Arrow”</div>

        <hr/>

        <button @click="deleteSelected">Delete Selected</button>
        <button @click="saveAsPng">Save as PNG</button>
        <button @click="exportXML">Export as XML</button>
      </div>

      <!-- 右侧画布 -->
      <div class="canvas-container">
        <canvas ref="fabricCanvas" width = 1200px height = 800px></canvas>
      </div>
    </div>
  </div>
</template>

<script>
import * as fabric from 'fabric'; // 如果 fabric 版本是 5.x，请使用合适的导入方式

export default {
  name: 'FabricDemo',
  data() {
    return {
      canvas: null,           // Fabric.js Canvas 实例
      arrowFromIndex: null,   // 下拉框选中的“箭头起点”shape下标
      arrowToIndex: null,     // 下拉框选中的“箭头终点”shape下标
    };
  },
  computed: {
    // 形状列表（只包含普通的 group，即包含矩形/圆 + 文本，不包含arrow）
    shapeGroups() {
      return this.getAllShapeGroups().map((group, idx) => {
        // 提取该 group 的文本，用于下拉框显示
        const textLabel = this.getTextInGroup(group) || ('Shape ' + idx);
        return { group, textLabel };
      });
    },
  },
  mounted() {
    // 初始化 Fabric.js 画布
    this.canvas = new fabric.Canvas(this.$refs.fabricCanvas);

    // 监听事件：当对象被修改（移动/缩放）后，更新箭头
    this.canvas.on('object:modified', (e) => {
      const obj = e.target;
      if (obj?.type === 'group' && !obj.arrowType) {
        // 遍历所有箭头，若箭头起点/终点与该对象关联，则更新
        const arrowGroups = this.canvas.getObjects().filter(o => o.arrowType === 'arrow');
        arrowGroups.forEach((arrowG) => {
          if (arrowG.fromGroupId === obj.id || arrowG.toGroupId === obj.id) {
            console.log("test...")
            this.updateArrowByShapes(arrowG);
          }
        });
      }
    });

    // 对象被删除后，刷新下拉框（vue computed 自动更新，不一定需要）
    this.canvas.on('object:removed', () => {
      // this.shapeGroups 会自动更新，所以无需手动刷新
    });

    // 监听双击，让文字可编辑
    this.canvas.on('mouse:dblclick', (opt) => {
      const target = this.canvas.findTarget(opt.e, true);
      if (!target) return;
      if (target.type === 'group' && !target.arrowType) {
        const iTextObj = target._objects.find(o => o.type === 'i-text');
        if (iTextObj) {
          iTextObj.enterEditing();
          iTextObj.selectAll();
          this.canvas.setActiveObject(iTextObj);
        }
      }
    });

    // 如果点空白处，且当前是Text正在编辑，则退出编辑
    this.canvas.on('mouse:down', (opt) => {
      const target = this.canvas.findTarget(opt.e);
      const activeObject = this.canvas.getActiveObject();
      if (!target && activeObject && activeObject.type === 'i-text' && activeObject.isEditing) {
        activeObject.exitEditing();
        this.canvas.discardActiveObject();
        this.canvas.renderAll();
      }
    });
  },
  methods: {
    /** ========== 创建矩形 + IText Group ========== */
    createRectWithText(left, top) {
      const rect = new fabric.Rect({
        width: 120,
        height: 60,
        fill: 'grey',
        originX: 'center',
        originY: 'center',
        rx: 5,
        ry: 5,
      });
      const iText = new fabric.IText('Double Click Edit', {
        fontSize: 16,
        fill: 'black',
        originX: 'center',
        originY: 'center',
      });
      const group = new fabric.Group([rect, iText], {
        left,
        top,
        objectCaching: false, // 禁用缓存，文字立即刷新
      });
      this.attachTextListenersToGroup(group);
      return group;
    },
    /** ========== 创建圆形 + IText Group ========== */
    createCircleWithText(left, top) {
      const circle = new fabric.Circle({
        radius: 40,
        fill: 'grey',
        originX: 'center',
        originY: 'center',
      });
      const iText = new fabric.IText('Double Click Edit', {
        fontSize: 16,
        fill: 'black',
        originX: 'center',
        originY: 'center',
      });
      const group = new fabric.Group([circle, iText], {
        left,
        top,
        objectCaching: false,
      });
      this.attachTextListenersToGroup(group);
      return group;
    },
    /** ========== 生成随机坐标，避免重叠 ========== */
    getRandomPosition(rangeX, rangeY) {
      return {
        left: Math.random() * rangeX,
        top:  Math.random() * rangeY,
      };
    },
    /** ========== 给 Group 上的文本添加监听，当编辑结束时刷新下拉框 ========== */
    attachTextListenersToGroup(group) {
      const iTextObj = group._objects.find(o => o.type === 'i-text');
      if (iTextObj) {
        iTextObj.on('editing:exited', () => {
          // 文字被编辑后，vue会自动重新计算 shapeGroups
        });
      }
    },
    /** ========== 获取 Group 中的文字 ========== */
    getTextInGroup(group) {
      if (!group || !group._objects) return '';
      const iTextObj = group._objects.find(o => o.type === 'i-text');
      return iTextObj ? iTextObj.text : '';
    },
    /** ========== 获取所有 group（排除箭头） ========== */
    getAllShapeGroups() {
      return this.canvas
        ?.getObjects()
        .filter(o => o.type === 'group' && !o.arrowType) || [];
    },
    /** ========== 添加矩形 ========== */
    addRect() {
      const pos = this.getRandomPosition(600, 400);
      const group = this.createRectWithText(pos.left, pos.top);
      group.id = `shape-${Date.now()}`; // 生成唯一 id
      this.canvas.add(group);
      this.canvas.setActiveObject(group);
      this.canvas.renderAll();
    },
    /** ========== 添加圆形 ========== */
    addCircle() {
      const pos = this.getRandomPosition(600, 400);
      const group = this.createCircleWithText(pos.left, pos.top);
      group.id = `shape-${Date.now()}`; // 生成唯一 id
      this.canvas.add(group);
      this.canvas.setActiveObject(group);
      this.canvas.renderAll();
    },
    /** ========== Delete Selected ========== */
    deleteSelected() {
      const activeObject = this.canvas.getActiveObject();
      if (activeObject) {
        this.canvas.remove(activeObject);
        this.canvas.discardActiveObject();
        this.canvas.renderAll();
      }
    },
    /** ========== Save as PNG ========== */
    saveAsPng() {
      const dataURL = this.canvas.toDataURL({ format: 'png', quality: 1.0 });
      const link = document.createElement('a');
      link.href = dataURL;
      link.download = 'myCanvas.png';
      link.click();
    },
    /** ========== 导出 XML ========== */
    exportXML() {
      /**
       * 只存：
       * 1) 所有“形状Group”的文字（并分配一个 id）
       * 2) 形状与形状间箭头指向关系（from / to）
       */
      const shapeGroups = this.getAllShapeGroups();
      const arrowGroups = this.canvas.getObjects().filter(o => o.arrowType === 'arrow');

      const groupIdMap = new Map();
      const shapes = [];
      shapeGroups.forEach((g, index) => {
        const label = this.getTextInGroup(g);
        shapes.push({ id: index, label });
        groupIdMap.set(g, index);
      });

      const arrows = arrowGroups.map((arrowG) => {
        const fromId = groupIdMap.get(arrowG.fromGroup);
        const toId = groupIdMap.get(arrowG.toGroup);
        return { from: fromId, to: toId };
      });

      let xml = '<diagram>\n';
      xml += '  <shapes>\n';
      shapes.forEach((s) => {
        xml += `    <shape id="${s.id}" label="${s.label}"></shape>\n`;
      });
      xml += '  </shapes>\n';
      xml += '  <arrows>\n';
      arrows.forEach((a) => {
        xml += `    <arrow from="${a.from}" to="${a.to}"></arrow>\n`;
      });
      xml += '  </arrows>\n';
      xml += '</diagram>';

      // 触发下载
      const blob = new Blob([xml], { type: 'text/xml' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'myCanvas.xml';
      link.click();
    },

    /** ========== 点击“Add Arrow” ========== */
    addArrow() {
      const fromIdx = this.arrowFromIndex;
      const toIdx   = this.arrowToIndex;
      if (fromIdx == null || toIdx == null) {
        alert("没有可用的形状，请先添加矩形或圆形。");
        return;
      }
      if (fromIdx === toIdx) {
        alert("起点和终点不能相同！");
        return;
      }
      const shapeGroups = this.getAllShapeGroups();
      const fromGroup = shapeGroups[fromIdx];
      const toGroup   = shapeGroups[toIdx];
      if (!fromGroup || !toGroup) {
        alert("选中的形状对象不存在！");
        return;
      }

      // 连线起终点
      const { startPoint, endPoint } = this.getConnectionPoints(fromGroup, toGroup);

      // 创建线段
      const line = new fabric.Line([startPoint.x, startPoint.y, endPoint.x, endPoint.y], {
        stroke: 'black',
        strokeWidth: 2,
        selectable: false,
      });

      // 箭头三角形
      const angle = Math.atan2(endPoint.y - startPoint.y, endPoint.x - startPoint.x);
      const triangle = new fabric.Triangle({
        left: endPoint.x,
        top: endPoint.y,
        originX: 'center',
        originY: 'center',
        width: 10,
        height: 15,
        fill: 'black',
        angle: (angle * 180) / Math.PI + 90,
        selectable: false,
      });

      // 箭头文本
      const arrowLabel = new fabric.Text(
        this.getTextInGroup(fromGroup) + " → " + this.getTextInGroup(toGroup),
        {
          left: (startPoint.x + endPoint.x) / 2,
          top:  (startPoint.y + endPoint.y) / 2 - 20,
          fontSize: 14,
          fill: 'green',
          selectable: false,
        }
      );

      // 组合
      const arrowGroup = new fabric.Group([line, triangle, arrowLabel], {
        hasControls: false,
        arrowType: 'arrow',
        fromGroup,
        toGroup,
        fromGroupId: fromGroup.id,  // 这里存 ID
        toGroupId: toGroup.id
      });

      this.canvas.add(arrowGroup);
      this.canvas.setActiveObject(arrowGroup);
    },

    /** ========== 计算形状边缘与连线（fromCenter->toCenter）的交点 ========== */
    getEdgeIntersection(shape, fromCenter, toCenter) {
      const dx = toCenter.x - fromCenter.x;
      const dy = toCenter.y - fromCenter.y;

      if (shape.type === 'circle') {
        const angle = Math.atan2(dy, dx);
        return {
          x: fromCenter.x + shape.radius * Math.cos(angle),
          y: fromCenter.y + shape.radius * Math.sin(angle),
        };
      } else if (shape.type === 'rect') {
        const halfWidth = shape.width / 2;
        const halfHeight = shape.height / 2;
        const scaleX = halfWidth / Math.abs(dx);
        const scaleY = halfHeight / Math.abs(dy);
        const scale = Math.min(scaleX, scaleY);
        return {
          x: fromCenter.x + dx * scale,
          y: fromCenter.y + dy * scale,
        };
      }
      return fromCenter; // 默认
    },

    /** ========== 根据 Group 中形状 + centerPoint 获取连线起终点 ========== */
    getConnectionPoints(fromGroup, toGroup) {
      const fromCenter = fromGroup.getCenterPoint();
      const toCenter = toGroup.getCenterPoint();
      const fromShape = fromGroup._objects.find(o => o.type !== 'i-text');
      const toShape = toGroup._objects.find(o => o.type !== 'i-text');

      const startPoint = this.getEdgeIntersection(fromShape, fromCenter, toCenter);
      const endPoint   = this.getEdgeIntersection(toShape, toCenter, fromCenter);
      return { startPoint, endPoint };
    },

    /** ========== 更新箭头位置：由 arrowGroup 中保存的 fromGroup / toGroup 来重新计算 ========== */
    updateArrowByShapes(arrowGroup) {
      const fromG = arrowGroup.fromGroup;
      const toG = arrowGroup.toGroup;
      if (!fromG || !toG) return;

      // 获取形状边缘连接点（基于画布全局坐标系）
      const { startPoint, endPoint } = this.getConnectionPoints(fromG, toG);

      // 直接更新线的全局坐标（自动处理组内偏移）
      const line = arrowGroup.item(0);
      line.set({
        x1: startPoint.x - arrowGroup.left, // 转换为组内本地坐标
        y1: startPoint.y - arrowGroup.top,
        x2: endPoint.x - arrowGroup.left,
        y2: endPoint.y - arrowGroup.top
      });

      // 更新箭头三角形
      const triangle = arrowGroup.item(1);
      const angle = Math.atan2(
        endPoint.y - startPoint.y,
        endPoint.x - startPoint.x
      );
      triangle.set({
        left: endPoint.x - arrowGroup.left, // 本地坐标
        top: endPoint.y - arrowGroup.top,
        angle: (angle * 180) / Math.PI + 90
      });

      // 更新文本位置（基于全局坐标转换）
      const text = arrowGroup.item(2);
      text.set({
        left: (startPoint.x + endPoint.x) / 2 - arrowGroup.left,
        top: (startPoint.y + endPoint.y) / 2 - arrowGroup.top - 20
      });

      // 关键步骤：更新整个箭头组的位置（保持内部坐标的本地性）
      arrowGroup.set({
        left: Math.min(startPoint.x, endPoint.x),
        top: Math.min(startPoint.y, endPoint.y)
      });

      arrowGroup.setCoords();
      this.canvas.requestRenderAll();
    },

    // updateArrowByShapes(arrowGroup) {
    //   const fromG = arrowGroup.fromGroup;
    //   const toG   = arrowGroup.toGroup;
    //   if (!fromG || !toG) return;

    //   console.log("arrow position changing...")
    //   // 先移除旧箭头
    //   this.canvas.remove(arrowGroup);

    //   const { startPoint, endPoint } = this.getConnectionPoints(fromG, toG);

    //   const minX = Math.min(startPoint.x, endPoint.x);
    //   const minY = Math.min(startPoint.y, endPoint.y);

    //   const localX1 = startPoint.x - minX;
    //   const localY1 = startPoint.y - minY;
    //   const localX2 = endPoint.x   - minX;
    //   const localY2 = endPoint.y   - minY;

    //   const line = new fabric.Line([localX1, localY1, localX2, localY2], {
    //     stroke: 'black',
    //     strokeWidth: 2,
    //     selectable: false,
    //   });

    //   const angle = Math.atan2(localY2 - localY1, localX2 - localX1);
    //   const triangle = new fabric.Triangle({
    //     left: localX2,
    //     top:  localY2,
    //     originX: 'center',
    //     originY: 'center',
    //     width: 10,
    //     height: 15,
    //     fill: 'black',
    //     angle: (angle * 180) / Math.PI + 90,
    //     selectable: false,
    //   });

    //   const arrowLabel = new fabric.Text("Arrow", {
    //     left: (localX1 + localX2) / 2,
    //     top:  (localY1 + localY2) / 2 - 20,
    //     fontSize: 14,
    //     fill: 'green',
    //     selectable: false,
    //   });

    //   const newArrowGroup = new fabric.Group([line, triangle, arrowLabel], {
    //     left: minX,
    //     top:  minY,
    //     hasControls: false,
    //     arrowType: 'arrow',
    //     fromGroup: fromG,
    //     toGroup:   toG,
    //   });

    //   this.canvas.add(newArrowGroup);
    //   this.canvas.renderAll();
    // },
  },
};
</script>

<style scoped>
/* 让整个页面铺满屏幕 */
.fabric-demo {
  display: flex;
  flex-direction: column;
  height: 100vh;
  margin: 0;
  padding: 0;
}

/* 指导信息 */
.instruction {
  text-align: center;
  font-size: 16px;
  padding: 10px;
  background-color: #f5f5f5;
  margin: 0;
  border-bottom: 1px solid #ddd;
}

/* 主体布局 */
.main-container {
  display: flex;
  flex-grow: 1;
  height: calc(100vh - 40px); /* 预留 space 给 instruction */
}

/* 左侧工具栏 */
.toolbar-container {
  width: 250px;
  height: 100%;
  border-right: 1px solid #ccc;
  box-sizing: border-box;
  padding: 10px;
  background-color: #fafafa;
  overflow-y: auto; /* 避免内容过多时溢出 */
}

/* 画布容器 */
.canvas-container {
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* 让 canvas 自适应填充 */
canvas {
  width: 100%;
  height: 100%;
  border: 1px solid #ccc;
}

button {
  display: block;
  margin-bottom: 10px;
  width: 100%;
  box-sizing: border-box;
}

select {
  margin-bottom: 10px;
  width: 100%;
  box-sizing: border-box;
}

.small-info {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
}
</style>