import config from "@/config";
import { v4 as uuidv4 } from 'uuid';
import { validateNodeAndInstance, blockIfPendingNewNode } from './operationUtils';
import { updateLinkWeight } from './linkUtils';
import { saveCurrentInstance } from './instanceUtils';
import { zoomToNode } from './clickUtils'; 

/**
 * 添加节点
 * @param {*} ctx
 */
export function addNewNode(ctx) {
  if (blockIfPendingNewNode(ctx)) return;

  ctx.isAddingNewNode = true; // 标记正在新增节点
  ctx.undoStack.push({
    ...deepCopyWithLinks(ctx),
    userOperations: JSON.parse(JSON.stringify(ctx.userOperations)),
  });

  const tempNodeName = `New Node`;  // 生成临时的节点 name
  const tempId = uuidv4();          // 生成临时的节点 id
  const newNode = {
    tempId,
    name: tempNodeName,
    type: "",
    color: "#D3B5E5",
    weight: 1,
    source: ctx.clickedNodeName,
    isThirdElement: true,
    size: 10,
    x: Math.random() * window.innerWidth, // 随机初始X坐标
    y: Math.random() * window.innerHeight, // 随机初始Y坐标
    editableName: true, // 新增时允许编辑
  };

  const nodeMap = new Map(ctx.nodes.map(node => [node.name, node]));
  ctx.nodes.push(newNode);
  nodeMap.set(newNode.name, newNode);

  const sourceNode = nodeMap.get(ctx.clickedNodeName);
  if (!sourceNode) {
    throw new Error(`Source node with name "${ctx.clickedNodeName}" not found.`);
  }

  const newLink = {
    source: sourceNode,
    target: newNode,
    value: 1,
    distance: 100,
    color: sourceNode.color || "#999999",
  };
  ctx.links.push(newLink);

  // 为新节点创建实例
  const defaultQuestion = "Just like what is mentioned in the story, Avery is currently facing difficulties in both their relationships with colleagues and their work performance. Do you believe Avery’s current situation is primarily a result of their actions? Please share your thoughts.";
  const newInstance = {
    name: "New Node", // 默认名称与节点一致
    category_: "",
    attribution_type_: "",
    type: "",
    question: defaultQuestion,
    opinion: "",
    editableName: true, // 允许编辑名称
    isNew: true, // 标记为新实例
    hasInitialLink: true,
    source: ctx.clickedNodeName,
  };

  ctx.selectedNodeName = tempNodeName;
  if (!ctx.thirdElementToInstances[tempNodeName]) {
    ctx.thirdElementToInstances[tempNodeName] = [];
  }
  
  ctx.thirdElementToInstances[tempNodeName].push(newInstance);
  ctx.selectedInstances = [newInstance]; // 更新实例
  ctx.currentIndex = 0; // 指向新增实例
  ctx.isInstanceContentVisible = true; // 显示右侧编辑框
  ctx.isEditMode = true;
  ctx.isNodeEditMode = true;

  ctx.links = fixLinkReferences(ctx.nodes, ctx.links);
  ctx.mainGroup.selectAll("*").remove(); // 清空现有图形
  ctx.renderGraph(); // 重新渲染图形
}

/**
 * 检查有没有重名的节点
 * @param {*} instanceToSave 
 * @param {*} ctx 
 * @returns 
 */
async function getDuplicateNode(instanceToSave, ctx) {
  try {
    const localDuplicate = ctx.nodes.find(
      node =>
        node.name === instanceToSave.name &&
        node.name !== ctx.selectedNodeName // 确保不是当前节点自己
    );
    if (localDuplicate) {
      console.log("在本地数据中找到同名节点:", localDuplicate);
      return localDuplicate; // 直接返回本地节点
    }

    const response = await fetch(`${config.baseURL}/api/${ctx.userId}/nodes/name/${instanceToSave.name}`);
    if (!response.ok) {
      if (response.status === 404) {
        return null; // 后端没有找到，返回 null
      }
      throw new Error("Error fetching node data");
    }

    const serverDuplicate = await response.json();
    console.log("在后端数据库中找到同名节点:", serverDuplicate);
    return serverDuplicate;

  } catch (error) {
    console.error("Error fetching node:", error);
    return null;
  }
}

/**
 * 保存节点
 * @param {*} ctx
 */
export async function saveCurrentNode(ctx) {
  const instanceToSave = ctx.selectedInstances[ctx.currentIndex];
  validateNodeAndInstance(ctx, instanceToSave);

  if (Object.keys(ctx.validationErrors).length > 0) {
    console.error("Validation errors:", ctx.validationErrors);
    return; 
  }

  const duplicateNode = await getDuplicateNode(instanceToSave, ctx);
  console.log(duplicateNode)

  /** 保存节点时有重名的节点：需要进行 instance 的合并 */
  if (duplicateNode) {
    console.log(duplicateNode)
    let existingNode = ctx.nodes.find(n => n.name === duplicateNode.name);
    if (!existingNode) {
        ctx.nodes.push(duplicateNode);
    }

    // 1) 合并到已有节点的逻辑 
    const selectedNodeObject = ctx.nodes.find(n => n.name === ctx.selectedNodeName);
    if (selectedNodeObject) {
      // 1.1 找出 当前正在编辑的节点 并删除相关的 link 
      const linksToRemap = ctx.links.filter(
        l => l.source.name === selectedNodeObject.name || l.target.name === selectedNodeObject.name
      );
      for (const oldLink of linksToRemap) {
        // 由于这个边还没有更新到数据库所以不需要记录操作，只需要在前端删除即可
        const index = ctx.links.indexOf(oldLink);
        if (index !== -1) {
          ctx.links.splice(index, 1);
        }
      }
      // 1.2 删除 当前正在编辑的节点
      const idx = ctx.nodes.findIndex(n => n.name === selectedNodeObject.name);
      if (idx !== -1) {
        ctx.isDirty = true;
        ctx.nodes.splice(idx, 1);
      }
    }
    // 2) 把当前 instance 变成 duplicateNode 的新实例 
    const newInstance = {
      tempId: uuidv4(),
      name: duplicateNode.name, // 与 duplicateNode 同名
      category_: instanceToSave.category_,
      attribution_type_: instanceToSave.attribution_type_,
      type: instanceToSave.type,
      question: instanceToSave.question,
      opinion: instanceToSave.opinion,
      isNew: true, 
      editableName: false, // 是否让用户继续改名字
      source: instanceToSave.source,
    };

    if (!ctx.thirdElementToInstances[duplicateNode.name]) {
      ctx.thirdElementToInstances[duplicateNode.name] = [];
    }
    ctx.thirdElementToInstances[duplicateNode.name].push(newInstance);

    const instCreateOpData = {
      tempId: newInstance.tempId,
      category_: newInstance.category_,
      attribution_type_: newInstance.attribution_type_,
      type: newInstance.type,
      question: newInstance.question,
      opinion: newInstance.opinion,
      name: newInstance.name, // 归属 nodeName
      source: instanceToSave.source,
    };
    const instCreateOperation = {
      userId: ctx.userId,
      operationType: "INSTANCE_CREATE",
      operationData: JSON.stringify(instCreateOpData),
    };
    ctx.userOperations.push(instCreateOperation);
    ctx.isDirty = true;

    updateLinkWeight(ctx, newInstance);

    // 3) 更新前端显示的 UI
    ctx.selectedNodeName = duplicateNode.name;
    ctx.selectedInstances = ctx.thirdElementToInstances[duplicateNode.name];
    ctx.currentIndex = ctx.selectedInstances.length - 1;
    ctx.isAddingNewNode = false;
    ctx.isInstanceContentVisible = true;
    ctx.isNodeEditMode = false;
    ctx.isEditMode = false;
    ctx.mainGroup.selectAll("*").remove();
    ctx.renderGraph();

    const savedNode = ctx.nodes.find(node => node.name === ctx.selectedNodeName);
    if (savedNode) {
      zoomToNode(ctx, savedNode, 5);
    }
    return;
  }
  
  // const serverNode = await getDuplicateNode(instanceToSave, ctx);
  // if(serverNode) {
  //   ctx.nodes.push(serverNode);
    
  //   const newInstance = {
  //     tempId: uuidv4(),
  //     name: serverNode.name, // 与 duplicateNode 同名
  //     category_: instanceToSave.category_,
  //     attribution_type_: instanceToSave.attribution_type_,
  //     type: instanceToSave.type,
  //     question: instanceToSave.question,
  //     opinion: instanceToSave.opinion,
  //     isNew: true, 
  //     editableName: false, // 是否让用户继续改名字
  //     source: instanceToSave.source,
  //   };

  //   if (!ctx.thirdElementToInstances[serverNode.name]) {
  //     ctx.thirdElementToInstances[serverNode.name] = [];
  //   }
  //   ctx.thirdElementToInstances[serverNode.name].push(newInstance);

  //   const instCreateOpData = {
  //     tempId: newInstance.tempId,
  //     category_: newInstance.category_,
  //     attribution_type_: newInstance.attribution_type_,
  //     type: newInstance.type,
  //     question: newInstance.question,
  //     opinion: newInstance.opinion,
  //     name: newInstance.name, // 归属 nodeName
  //     source: instanceToSave.source,
  //   };
  //   const instCreateOperation = {
  //     userId: ctx.userId,
  //     operationType: "INSTANCE_CREATE",
  //     operationData: JSON.stringify(instCreateOpData),
  //   };
  //   ctx.userOperations.push(instCreateOperation);
  //   ctx.isDirty = true;

  //   updateLinkWeight(ctx, newInstance);

  //   ctx.isDirty = true;
  //   ctx.selectedNodeName = serverNode.name;
  //   ctx.selectedInstances = ctx.thirdElementToInstances[serverNode.name];
  //   ctx.currentIndex = ctx.selectedInstances.length - 1;

  //   ctx.isAddingNewNode = false;
  //   ctx.isInstanceContentVisible = true;
  //   ctx.isNodeEditMode = false;
  //   ctx.isEditMode = false;

  //   ctx.mainGroup.selectAll("*").remove();
  //   ctx.renderGraph();

  //   // 若需要放大/定位到新链接或服务器端节点
  //   zoomToNode(ctx, serverNode, 5);
  //   return;
  // }

  /** 保存节点时没有重名的节点：这是一个新节点 */
  if (instanceToSave.isNew) {
    const selectedNode = ctx.nodes.find(node => node.name === ctx.selectedNodeName);
    selectedNode.name = instanceToSave.name;
    selectedNode.type = instanceToSave.type;
    selectedNode.editableName = false;
    instanceToSave.editableName = false;
    ctx.selectedNodeName = instanceToSave.name;

    // 记录 `NODE_CREATE` 操作
    const nodeOpData = {
      tempId: selectedNode.tempId,
      nodeName: selectedNode.name,
      type: selectedNode.type,
      color: selectedNode.color,
      weight: selectedNode.weight,
      source: selectedNode.source,
      isThirdElement: selectedNode.isThirdElement,
      x: selectedNode.x, // 保存节点的 x 坐标
      y: selectedNode.y, // 保存节点的 y 坐标
    };
    const nodeOperation = {
      userId: ctx.userId,
      operationType: "NODE_CREATE",
      operationData: JSON.stringify(nodeOpData),
    };
    ctx.userOperations.push(nodeOperation);

    // 记录 LINK_CREATE 操作
    const sourceNode = ctx.nodes.find(node => node.name === selectedNode.source);
    if (sourceNode) {
      const tempId = uuidv4();
      const linkCreateOp = {
        userId: ctx.userId,
        operationType: "LINK_CREATE",
        operationData: JSON.stringify({
          tempId: tempId,
          source: sourceNode,
          target: selectedNode,
          value: 1,
          distance: 100,
          color: sourceNode.color || "#999999",
        }),
      };
      ctx.userOperations.push(linkCreateOp);
      const localLink = ctx.links.find(
        link => link.source.name === sourceNode.name && link.target.name === selectedNode.name
      );
      if (localLink) {
        localLink.tempId = tempId;  // ✅ 这里补上 tempId
        console.log(`Updated link with tempId: ${tempId}`, localLink);
      } else {
        console.warn("Failed to find link in ctx.links for tempId update");
      }
    }
    ctx.isDirty = true;
  }

  ctx.isAddingNewNode = false;
  ctx.isEditMode = false;
  ctx.isNodeEditMode = false;
  saveCurrentInstance(ctx); // 保存实例
  ctx.links = fixLinkReferences(ctx.nodes, ctx.links);
  ctx.mainGroup.selectAll("*").remove(); 
  ctx.renderGraph(); 

  const savedNode = ctx.nodes.find(node => node.name === ctx.selectedNodeName);
  if (savedNode) {
    zoomToNode(ctx, savedNode, 5);
  }
}


/**
 * 删除节点
 * @param {*} ctx
 * @param {*} nodeName
 */
export async function deleteNode(ctx, nodeName) {
  ctx.undoStack.push({
    ...deepCopyWithLinks(ctx),
    selectedInstances: JSON.parse(JSON.stringify(ctx.selectedInstances)),
    selectedNodeName: ctx.selectedNodeName,
    isInstanceContentVisible: ctx.isInstanceContentVisible,
  });

  const nodeIndex = ctx.nodes.findIndex(n => n.name === nodeName);
  if (nodeIndex !== -1) {
    // 1️. 先找到被删除的 Node
    const deletedNode = ctx.nodes[nodeIndex];

    // 2️. 删除该节点下的所有 Instance
    const instancesToDelete = ctx.thirdElementToInstances[nodeName] || [];
    for (const inst of instancesToDelete) {
      const instDeleteOp = {
        userId: ctx.userId,
        operationType: "INSTANCE_DELETE",
        operationData: JSON.stringify({
          instanceId: inst.id || inst.tempId,
          name: inst.name,
        }),
      };
      ctx.userOperations.push(instDeleteOp);
    }

    // 3️. 记录删除 Node 操作
    const nodeDeleteOp = {
      userId: ctx.userId,
      operationType: "NODE_DELETE",
      operationData: JSON.stringify({
        nodeId: deletedNode.id || deletedNode.tempId,
        nodeName: deletedNode.name,
      }),
    };
    ctx.userOperations.push(nodeDeleteOp);
    ctx.isDirty = true;

    // 4️. 从 ctx 中移除 Node 和它的 Instances
    ctx.nodes.splice(nodeIndex, 1);
    delete ctx.thirdElementToInstances[nodeName];

    // 5️. 删除相关 Links
    ctx.links = ctx.links.filter(l => l.source.name !== nodeName && l.target.name !== nodeName);
    
    ctx.mainGroup.selectAll("*").remove();
    ctx.renderGraph();
  }
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