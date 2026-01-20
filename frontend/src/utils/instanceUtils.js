import { v4 as uuidv4 } from 'uuid';
import { validateNodeAndInstance } from './operationUtils';
import { deleteNode } from './nodeUtils';
import { createOrAddLinkValue, updateLinkWeight, reduceLinkValue, deleteLink } from './linkUtils';

/**
 * 编辑实例
 * @param {*} ctx
 */
export function EditInstance(ctx) {
  ctx.undoStack.push({
    selectedInstances: JSON.parse(JSON.stringify(ctx.selectedInstances)),
    selectedNodeName: ctx.selectedNodeName,
    nodes: JSON.parse(JSON.stringify(ctx.nodes)),
    links: JSON.parse(JSON.stringify(ctx.links)),
    isInstanceContentVisible: ctx.isInstanceContentVisible,
  });
  // 进入编辑模式并备份原数据
  ctx.originalInstances = JSON.parse(JSON.stringify(ctx.selectedInstances));
  ctx.isEditMode = true;

  ctx.selectedInstances.forEach(instance => {
    instance.editableName = true;
  });
}

/**
 * 新增实例
 * @param {*} ctx
 */
export function addNewInstance(ctx) {
  ctx.undoStack.push({
    selectedInstances: JSON.parse(JSON.stringify(ctx.selectedInstances)),
    selectedNodeName: ctx.selectedNodeName,
    nodes: JSON.parse(JSON.stringify(ctx.nodes)),
    links: JSON.parse(JSON.stringify(ctx.links)),
    isInstanceContentVisible: ctx.isInstanceContentVisible,
  });

  const currentNode = ctx.nodes.find(n => n.name === ctx.selectedNodeName);
  ctx.originalInstances = JSON.parse(JSON.stringify(ctx.selectedInstances));
  const defaultQuestion = "Just like what is mentioned in the story, Avery is currently facing difficulties in both their relationships with colleagues and their work performance. Do you believe Avery’s current situation is primarily a result of their actions? Please share your thoughts.";
  const newEmptyInstance = {
    category_: "",
    attribution_type_: "",
    type: "",
    question: defaultQuestion,
    opinion: "",
    name: ctx.selectedNodeName,
    isNew: true, // 标记为新实例
    editableName: false, // 新增实例时禁用编辑 name
    source: currentNode?.source || "", 
  };
  ctx.selectedInstances.push(newEmptyInstance);
  ctx.currentIndex = ctx.selectedInstances.length - 1;
  ctx.isEditMode = true;
}

/**
 * 保存实例（新增/修改）
 * @param {*} ctx
 */
export async function saveCurrentInstance(ctx) {
  const instanceToSave = ctx.selectedInstances[ctx.currentIndex];
  validateNodeAndInstance(ctx, instanceToSave);

  if (Object.keys(ctx.validationErrors).length > 0) {
    console.error("Validation errors:", ctx.validationErrors);
    return; 
  }

  const oldName = ctx.selectedNodeName;     // 老 node 的 name
  const newName = instanceToSave.name;      // instance 改后的 name

  if (!instanceToSave.id) { // 为新增实例分配唯一 ID
    instanceToSave.id = uuidv4();
  }
  
  // 新增加的 instance 的名字和 node 不一样，需要分裂这个 instance 到新的 node
  if (newName !== oldName) { 
    ctx.undoStack.push({
      ...deepCopyWithLinks(ctx),
      thirdElementToInstances: JSON.parse(JSON.stringify(ctx.thirdElementToInstances)),
      selectedInstances: JSON.parse(JSON.stringify(ctx.selectedInstances)),
      selectedNodeName: ctx.selectedNodeName,
      isInstanceContentVisible: ctx.isInstanceContentVisible,
    });
    const existingNode = ctx.nodes.find(n => n.name === newName);
    if (existingNode) { // 合并到已有节点
      mergeInstanceToExistingNode(ctx, oldName, newName, instanceToSave);
    } else {  // 分裂并创建新 node
      splitInstanceToNewNode(ctx, oldName, newName, instanceToSave);
    }
    return;
  }

  // 新增加的 instance 的名字和 node 一样，只需要新建一个instance
  if (instanceToSave.isNew) {
    delete instanceToSave.isNew;

    if (!instanceToSave.hasInitialLink) {
      updateLinkWeight(ctx, instanceToSave);
    } else {
      // 如果已经有 hasInitialLink，就把它删除或设成 false，表示后面正常进行
      delete instanceToSave.hasInitialLink;
    }
    // 新建实例操作记录
    const opData = {
      tempId: instanceToSave.id,
      category_: instanceToSave.category_,
      attribution_type_: instanceToSave.attribution_type_,
      type: instanceToSave.type,
      question: instanceToSave.question,
      opinion: instanceToSave.opinion,
      name: instanceToSave.name,
      source: instanceToSave.source,
    };
    const operation = {
      userId: ctx.userId,
      operationType: "INSTANCE_CREATE",
      operationData: JSON.stringify(opData)
    };
    ctx.userOperations.push(operation);
    ctx.isDirty = true;

  } else {
    // 更新实例操作记录
    const opData = {
      instanceId: instanceToSave.tempId || instanceToSave.id,
      updatedFields: {
        category_: instanceToSave.category_,
        attribution_type_: instanceToSave.attribution_type_,
        type: instanceToSave.type,
        question: instanceToSave.question,
        opinion: instanceToSave.opinion,
        name: instanceToSave.name,
        source: instanceToSave.source
      }
    };
    const operation = {
      userId: ctx.userId,
      operationType: "INSTANCE_UPDATE",
      operationData: JSON.stringify(opData)
    };
    ctx.userOperations.push(operation);
    ctx.isDirty = true;
  }

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
  
  const nodeToUpdate = ctx.nodes.find(n => n.name === instanceToSave.name);
  if (nodeToUpdate) {
    // 记录旧值
    const oldType = nodeToUpdate.type;
    const oldColor = nodeToUpdate.color;

    // 假设想让节点的 type 与 instance 相同
    nodeToUpdate.type = instanceToSave.type;
    nodeToUpdate.color = typeToColorMap[nodeToUpdate.type];

    // 只有当 type 或 color 发生变化时，才记录 NODE_UPDATE 操作
    if (oldType !== nodeToUpdate.type || oldColor !== nodeToUpdate.color) {
      const nodeUpdateOp = {
        userId: ctx.userId,
        operationType: "NODE_UPDATE",
        operationData: JSON.stringify({
          nodeId: nodeToUpdate.id || nodeToUpdate.tempId,
          updatedFields: {
            name: nodeToUpdate.name,
            type: nodeToUpdate.type,
            color: nodeToUpdate.color
          }
        }),
      };
      ctx.userOperations.push(nodeUpdateOp);
      ctx.isDirty = true;
    }
  }

  ctx.thirdElementToInstances[ctx.selectedNodeName] = JSON.parse(JSON.stringify(ctx.selectedInstances));
  ctx.isEditMode = false;
  ctx.selectedInstances.forEach(instance => {
    instance.editableName = false;
  });
  ctx.mainGroup.selectAll("*").remove();
  ctx.renderGraph();
}

/**
 * 删除实例
 * @param {*} ctx
 * @param {*} index
 */
export function deleteInstance(ctx, index) {
  // 1. 记录当前状态到撤销栈
  ctx.undoStack.push({
    selectedInstances: JSON.parse(JSON.stringify(ctx.selectedInstances)),
    selectedNodeName: ctx.selectedNodeName,
    nodes: JSON.parse(JSON.stringify(ctx.nodes)),
    links: JSON.parse(JSON.stringify(ctx.links)),
    isInstanceContentVisible: ctx.isInstanceContentVisible,
  });

  // 2. 删除指定的实例
  if (index !== -1) {
    const deletedInstance = ctx.selectedInstances.splice(index, 1)[0];
    console.log("deletedInstance.id:", deletedInstance.id)
    reduceLinkValue(ctx, deletedInstance);
    // 2.2. 记录 INSTANCE_DELETE
    const opData = {
      instanceId: deletedInstance.tempId || deletedInstance.id,
      name: deletedInstance.name
    };
    const operation = {
      userId: ctx.userId,
      operationType: "INSTANCE_DELETE",
      operationData: JSON.stringify(opData)
    };
    ctx.userOperations.push(operation);
    ctx.isDirty = true;
  }

  // 3. 更新当前节点的实例列表
  ctx.thirdElementToInstances[ctx.selectedNodeName] = JSON.parse(
    JSON.stringify(ctx.selectedInstances)
  );

  // 4. 如果当前节点没有实例，则删除节点
  if (ctx.selectedInstances.length === 0) {
    deleteNode(ctx, ctx.selectedNodeName);
    ctx.isInstanceContentVisible = false;
    ctx.selectedNodeName = '';
  } else {
    if (ctx.currentIndex >= ctx.selectedInstances.length) {
      ctx.currentIndex = ctx.selectedInstances.length - 1;
    }
    ctx.mainGroup.selectAll("*").remove();
    ctx.renderGraph();
  }
}

/**
 * 将指定的 instance 从 oldNodeName 分裂到 newNodeName，创建一个新的 node 并将此 instance 迁移过去
 * @param {*} ctx 
 * @param {*} oldNodeName 
 * @param {*} newNodeName 
 * @param {*} instanceToMove 
 */
function splitInstanceToNewNode(ctx, oldNodeName, newNodeName, instanceToMove) {
  // 1) 找到旧 node
  const oldNode = ctx.nodes.find(n => n.name === oldNodeName);

  // 2) 处理 source 指向 oldNode 的链接
  if (instanceToMove.source) {
    const sourceNode = ctx.nodes.find(n => n.name === instanceToMove.source);
    if (sourceNode) {
      const link = ctx.links.find(
        l => l.source.name === sourceNode.name && l.target.name === oldNodeName
      );
      if (link) {
        link.value -= 1;  // 减少权重
        if (link.value <= 0) {  // 如果权重为 0，删除链接
          deleteLink(ctx, link);
        } else {
          // 记录 LINK_UPDATE 操作
          const linkUpdateOp = {
            userId: ctx.userId,
            operationType: "LINK_UPDATE",
            operationData: JSON.stringify({
              id: link.tempId || link.id,
              source: link.source.name,
              target: link.target.name,
              newValue: link.value,
              distance: link.distance,
              color: link.color,
            }),
          };
          ctx.userOperations.push(linkUpdateOp);
        }
      }
    }
  }

  // 3) 在图上创建一个新的 node
  const tempId = uuidv4();
  const newNode = {
    tempId,
    name: newNodeName,
    type: oldNode.type,
    color: oldNode.color,
    weight: oldNode.weight,
    source: oldNode.source,
    isThirdElement: true,
    size: 10,
    x: Math.random() * window.innerWidth, // 随机初始X坐标
    y: Math.random() * window.innerHeight, // 随机初始Y坐标
    editableName: false, // 新增时允许编辑
  };
  ctx.nodes.push(newNode);  // push 到 nodes

  const nodeCreateOp = {
    userId: ctx.userId,
    operationType: "NODE_CREATE",
    operationData: JSON.stringify({
      tempId,
      nodeName: newNode.name,
      type: newNode.type,
      color: newNode.color,
      weight: newNode.weight,
      source: newNode.source,
      x: newNode.x,
      y: newNode.y,
    }),
  };
  ctx.userOperations.push(nodeCreateOp);
  ctx.isDirty = true;

  // 4) 创建链接
  if (instanceToMove.source) {
    const sourceNode = ctx.nodes.find(n => n.name === instanceToMove.source);
    if (sourceNode) {
      const newLink = {
        tempId: uuidv4(),
        source: sourceNode,
        target: newNode,
        value: 1,
        distance: 100,
        color: sourceNode.color || "#999999",
      };
      ctx.links.push(newLink);

      const linkCreateOp = {
        userId: ctx.userId,
        operationType: "LINK_CREATE",
        operationData: JSON.stringify({
          tempId: newLink.tempId,
          source: newLink.source.name,
          target: newLink.target.name,
          value: newLink.value,
          distance: newLink.distance,
          color: newLink.color,
        }),
      };
      ctx.userOperations.push(linkCreateOp);
    }
  }

  // 5) 从 oldNodeName 的 instance 列表中删除 instanceToMove
  const oldList = ctx.thirdElementToInstances[oldNodeName] || [];
  const idx = oldList.findIndex(instance => instance.id === instanceToMove.id);
  if (idx !== -1) {
    oldList.splice(idx, 1);
  }

  // 5.1) 在操作记录中推送 "INSTANCE_DELETE"
  //      表示在 oldNodeName 里删除了 instance
  const deleteOpData = {
    instanceId: instanceToMove.tempId || instanceToMove.id,
    name: oldNodeName // 旧 node name
  };
  const deleteOperation = {
    userId: ctx.userId,
    operationType: "INSTANCE_DELETE",
    operationData: JSON.stringify(deleteOpData),
  };
  ctx.userOperations.push(deleteOperation);
  ctx.isDirty = true;

  // 6) 把这个 instance 改成归属 newNodeName
  //    并可把 isNew = true (让下次保存走 INSTANCE_CREATE？)
  instanceToMove.name = newNodeName;
  instanceToMove.isNew = true;
  instanceToMove.editableName = false; 

  // 7) 放到 newNodeName 的 instance 列表
  if (!ctx.thirdElementToInstances[newNodeName]) {
    ctx.thirdElementToInstances[newNodeName] = [];
  }
  ctx.thirdElementToInstances[newNodeName].push(instanceToMove);

  // 7.1) 在操作记录中推送 "INSTANCE_CREATE"
  //      表示在 newNodeName 里新建了一个 instance
  const createOpData = {
    tempId: instanceToMove.id,   // 记录这个实例新的 / 保留的 id
    category_: instanceToMove.category_,
    attribution_type_: instanceToMove.attribution_type_,
    type: instanceToMove.type,
    question: instanceToMove.question,
    opinion: instanceToMove.opinion,
    name: newNodeName,       // 归属 node
    source: instanceToMove.source,
  };
  const createOperation = {
    userId: ctx.userId,
    operationType: "INSTANCE_CREATE",
    operationData: JSON.stringify(createOpData),
  };
  ctx.userOperations.push(createOperation);
  ctx.isDirty = true;

  // 8) 如果 oldList 为空，则删除旧 node
  if (oldList.length === 0) {
    deleteNode(ctx, oldNodeName); // 老 node 没 instance 就消失
  } else {
    ctx.thirdElementToInstances[oldNodeName] = oldList; // 保留 old node, 但 instance 数量减少
  }

  // 9) 更新 UI
  ctx.selectedNodeName = newNodeName;
  ctx.selectedInstances = [instanceToMove];
  ctx.currentIndex = 0;
  ctx.isInstanceContentVisible = true;
  // 退出 edit
  ctx.isEditMode = false;
  ctx.isNodeEditMode = false;

  // 10) 重绘
  ctx.mainGroup.selectAll("*").remove();
  ctx.renderGraph();
}


/**
 * 将指定 instance 从 oldNodeName 移动到已存在的 newNodeName（合并）
 * 不创建新的 node，只将 instance 移动过去。并记录 INSTANCE_DELETE + INSTANCE_CREATE。
 * @param {*} ctx 
 * @param {*} oldNodeName 
 * @param {*} newNodeName 
 * @param {*} instanceToMove 
 */
export function mergeInstanceToExistingNode(ctx, oldNodeName, newNodeName, instanceToMove) {
  const oldName = oldNodeName;
  const oldSource = instanceToMove.source;

  // 1. 从 oldNodeName 下删除此 instance
  const oldList = ctx.thirdElementToInstances[oldNodeName] || [];
  const idx = oldList.findIndex(inst => inst.id === instanceToMove.id);
  if (idx !== -1) {
    oldList.splice(idx, 1);
    reduceLinkValue(ctx, { source: oldSource, name: oldName });
  }

  // 2. 记录 INSTANCE_DELETE
  const deleteOpData = {
    instanceId: instanceToMove.tempId || instanceToMove.id,
    name: oldNodeName,
  };
  const deleteOperation = {
    userId: ctx.userId,
    operationType: "INSTANCE_DELETE",
    operationData: JSON.stringify(deleteOpData),
  };
  ctx.userOperations.push(deleteOperation);
  ctx.isDirty = true;

  // 如果 oldNode 变空 => 可删除 oldNode
  if (oldList.length === 0) {
    deleteNode(ctx, oldNodeName);
  } else {
    ctx.thirdElementToInstances[oldNodeName] = oldList;
  }

  // 3. 把 instance 改为归属 newNodeName
  instanceToMove.name = newNodeName;
  // 给个新的 id 或者保留原 id 看你需求
  instanceToMove.editableName = false;
  const sourceNode = ctx.nodes.find(n => n.name === instanceToMove.source);
  const targetNode = ctx.nodes.find(n => n.name === newNodeName);
  if (sourceNode && targetNode) {
    createOrAddLinkValue(ctx, sourceNode, targetNode, 1, 100, sourceNode.color || '#999999');
  }

  // 4. 加到 newNodeName 的 instance list
  if (!ctx.thirdElementToInstances[newNodeName]) {
    ctx.thirdElementToInstances[newNodeName] = [];
  }
  ctx.thirdElementToInstances[newNodeName].push(instanceToMove);

  // 5. 记录 INSTANCE_CREATE
  const createOpData = {
    tempId: instanceToMove.id,
    category_: instanceToMove.category_,
    attribution_type_: instanceToMove.attribution_type_,
    type: instanceToMove.type,
    question: instanceToMove.question,
    opinion: instanceToMove.opinion,
    name: newNodeName,
    source: instanceToMove.source, 
  };
  const createOperation = {
    userId: ctx.userId,
    operationType: "INSTANCE_CREATE",
    operationData: JSON.stringify(createOpData),
  };
  ctx.userOperations.push(createOperation);
  ctx.isDirty = true;

  // 6. 更新 UI
  ctx.selectedNodeName = newNodeName;
  ctx.selectedInstances = ctx.thirdElementToInstances[newNodeName];
  ctx.currentIndex = ctx.selectedInstances.length - 1;
  ctx.isInstanceContentVisible = true;
  ctx.isEditMode = false;
  ctx.isNodeEditMode = false;

  // 重绘
  ctx.mainGroup.selectAll("*").remove();
  ctx.renderGraph();
}

/**
 * 深拷贝 nodes 和 links，并保留 links 的 source 和 target 引用
 * @param {*} ctx 
 * @returns 
 */
export function deepCopyWithLinks(ctx) {
  const nodeMap = new Map(ctx.nodes.map(node => [node.name, { ...node }]));
  
  const linksCopy = ctx.links.map(link => ({ // 深拷贝 links，同时保留 source 和 target 的引用
    ...link,
    source: typeof link.source === 'string' ? nodeMap.get(link.source) : nodeMap.get(link.source.name),
    target: typeof link.target === 'string' ? nodeMap.get(link.target) : nodeMap.get(link.target.name),
  }));

  return {
    nodes: Array.from(nodeMap.values()),
    links: linksCopy,
  };
}

/**
 * 有必要的话可以和 deepCopyWithLinks 合并
 * @param {*} nodes 
 * @param {*} links 
 * @returns 
 */
export function fixLinkReferences(nodes, links) {
  const nodeMap = new Map(nodes.map(node => [node.name, node])); // 创建节点映射表
  return links.map(link => ({
    ...link,
    source: typeof link.source === 'string' ? nodeMap.get(link.source) : nodeMap.get(link.source.name),
    target: typeof link.target === 'string' ? nodeMap.get(link.target) : nodeMap.get(link.target.name),
  }));
}