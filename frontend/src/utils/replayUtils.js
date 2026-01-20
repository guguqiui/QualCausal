/**
 * 根据操作类型转向不同方法
 * @param {*} userOperations 
 * @param {*} thirdElementToInstances 
 * @param {*} nodes 
 * @param {*} links 
 */
export function restoreUserState(userOperations, thirdElementToInstances, nodes, links) {

  let isCreateNewNode = false;

  if (!Array.isArray(userOperations)) {
    console.warn("Invalid userOperations:", userOperations);
    return { isCreateNewNode };
  }


  for (const op of userOperations) {
    const opType = op.operationType;

    let data;
    try {
      data = JSON.parse(op.operationData);
    } catch (error) {
      console.error("Failed to parse operationData:", op.operationData, error);
      continue;
    }

    switch (opType) {
      // ------------------ Instance 相关 ------------------
      case "INSTANCE_CREATE":
        addInstanceFromOperation(data, thirdElementToInstances);
        break;
      case "INSTANCE_UPDATE":
        updateInstanceFromOperation(data, thirdElementToInstances);
        break;
      case "INSTANCE_DELETE":
        deleteInstanceFromOperation(data, thirdElementToInstances);
        break;
          
      // ------------------ Node 相关 ------------------
      case "NODE_CREATE":
        createNodeFromOperation(data, nodes, links);
        // console.log("Restored node:", data.nodeName, "x:", data.x, "y:", data.y);
        isCreateNewNode = true;
        break;
      case "NODE_UPDATE":
        updateNodeFromOperation(data, nodes, links);
        break;
      case "NODE_DELETE":
        deleteNodeFromOperation(data, nodes, links);
        break;

      // ------------------ Link 相关 ------------------
      case "LINK_CREATE":
        createLinkFromOperation(data, nodes, links);
        break;
      case "LINK_UPDATE":
        updateLinkFromOperation(data, nodes, links);
        break;
      case "LINK_DELETE":
        deleteLinkFromOperation(data, nodes, links);
        break;

      default:
        console.warn(`Unknown operationType: ${opType}`);
    }
  }

  // 修复 links 的 source 和 target
  const nodeMap = new Map(nodes.map(node => [node.name, node]));
  links.forEach(link => {
    link.source = typeof link.source === 'string' ? nodeMap.get(link.source) : link.source;
    link.target = typeof link.target === 'string' ? nodeMap.get(link.target) : link.target;
  });

  // 检查并修复节点的初始位置
  nodes.forEach(node => {
    if (isNaN(node.x) || isNaN(node.y)) {
      console.warn(`Node ${node.name} has invalid position. Resetting to default.`);
      node.x = Math.random() * window.innerWidth;
      node.y = Math.random() * window.innerHeight;
    }
  });

  return isCreateNewNode;
}

// instanceData 结构：
// INSTANCE_CREATE: {category_, attribution_type_, type, question, opinion, name}
// INSTANCE_UPDATE: {instanceId, updatedFields: {...}}
// INSTANCE_DELETE: {instanceId, name}

/**
 * 添加新实例
 * @param {*} data 
 * @param {*} thirdElementToInstances 
 */
function addInstanceFromOperation(data, thirdElementToInstances) {
  const { name } = data;
  if (!thirdElementToInstances[name]) {
    thirdElementToInstances[name] = [];
  }
  // data本身包含所有实例字段(category_, attribution_type_, type, question, opinion, name)
  // 此处不需要id，因为新增实例尚未有id（可以是前端虚拟的id或后端分配后再更新）
  const newInstance = {
    ...data
  };
  thirdElementToInstances[name].push(newInstance);
}

/**
 * 更新实例
 * @param {*} data 
 * @param {*} thirdElementToInstances 
 */
function updateInstanceFromOperation(data, thirdElementToInstances) {
  const { instanceId, updatedFields } = data;
  // 我们需要根据instanceId在thirdElementToInstances中找到对应实例
  // 假设您在实例中有id字段存放 instanceId
  for (const nameKey in thirdElementToInstances) {
    const instances = thirdElementToInstances[nameKey];
    const inst = instances.find(i => i.id === instanceId);
    if (inst) {
      // console.log("Found instance to update:", inst);
      // 找到该实例后，应用updatedFields
      for (const field in updatedFields) {
        inst[field] = updatedFields[field];
      }
      break;
    }
  }
}

/**
 * 删除实例
 * @param {*} data 
 * @param {*} thirdElementToInstances 
 */
function deleteInstanceFromOperation(data, thirdElementToInstances) {
  const { instanceId, name } = data;
  // 在 thirdElementToInstances[name] 找到该实例并删除
  if (thirdElementToInstances[name]) {
    const instances = thirdElementToInstances[name];
    const index = instances.findIndex(i => i.id === instanceId);
    if (index !== -1) {
      instances.splice(index, 1);
    }
  }
}

// operationData 结构:
// NODE_CREATE: {nodeName, type, color, weight, ... links: [...]}
// NODE_UPDATE: {nodeName, updatedFields: {...}}
// NODE_DELETE: {nodeName}

/**
 * 添加新节点
 * @param {*} data 
 * @param {*} nodes 
 * @param {*} links 
 */
function createNodeFromOperation(data, nodes) {

    const TYPE_TO_COLOR_MAP = {
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
        "motivation": "#BFD7ED",
    };
    const computedColor = TYPE_TO_COLOR_MAP[data.type] || "#D3B5E5";

    // 检查 source 节点是否存在
    const sourceExists = nodes.some(node => node.name === data.source);
    if (!sourceExists) {
        console.warn(`Source node "${data.source}" does not exist. Node "${data.nodeName}" will not be added.`);
        return; // 不添加节点
    }

    const newNode = {   // 创建新节点对象
        name: data.nodeName,
        weight: data.weight,
        color: computedColor,
        type: data.type,
        source: data.source,
        isThirdElement: true,
        size: 10,
        x: data.x,
        y: data.y,
    };

    const nodeMap = new Map(nodes.map(node => [node.name, node]));
    nodes.push(newNode);
    nodeMap.set(newNode.name, newNode);

    // if (data.links && Array.isArray(data.links)) {
    //     for (const l of data.links) {
    //         const targetNode = nodeMap.get(l.targetNode); // 解析 targetNode
    //         if (targetNode) {
    //             links.push({
    //                 source: newNode,
    //                 target: targetNode,
    //                 value: l.value,
    //                 distance: l.distance,
    //                 color: l.color || "#999999"
    //             });
    //         }
    //     }
    // }
}

/**
 * 更新节点
 * @param {*} data 
 * @param {*} nodes 
 */
function updateNodeFromOperation(data, nodes) {
  const { nodeName, updatedFields } = data;
  const node = nodes.find(n => n.name === nodeName);
  if (node) {
    for (const field in updatedFields) {
      node[field] = updatedFields[field];
    }
  }

  // const nodeMap = new Map(nodes.map(node => [node.name, node]));
  // if (data.updatedLinks && Array.isArray(data.updatedLinks)) {
  //       for (const l of data.updatedLinks) {
  //           const targetNode = nodeMap.get(l.target); // 解析 targetNode
  //           const sourceNode = nodeMap.get(l.source);
  //           if (targetNode) {
  //               links.push({
  //                   source: sourceNode,
  //                   target: targetNode,
  //                   value: l.value,
  //                   distance: l.distance,
  //                   color: l.color || "#999999"
  //               });
  //           }
  //       }
  //   }
}

/**
 * 删除节点
 * @param {*} data 
 * @param {*} nodes 
 * @param {*} links 
 */
function deleteNodeFromOperation(data, nodes, links) {
  const { nodeName } = data;
  const nodeIndex = nodes.findIndex(n => n.name === nodeName);
  if (nodeIndex !== -1) {
    const node = nodes[nodeIndex];
    nodes.splice(nodeIndex, 1);

    // 删除与该节点相关的links
    for (let i = links.length - 1; i >= 0; i--) {
      const l = links[i];
      if (l.source === node || l.target === node) {
        links.splice(i, 1);
      }
    }
  }
}

/**
 * 创建链接
 * @param {*} data 
 * @param {*} nodes 
 * @param {*} links 
 * @returns 
 */
function createLinkFromOperation(data, nodes, links) {
    const nodeMap = new Map(nodes.map(n => [n.name, n]));
    const sourceNode = nodeMap.get(data.source);
    const targetNode = nodeMap.get(data.target);
    if (!sourceNode || !targetNode) {
        console.warn(`LINK_CREATE failed. source or target not found. source=${data.source}, target=${data.target}`);
        return;
    }

    // push 新 link
    links.push({
        source: sourceNode,
        target: targetNode,
        value: data.value ?? 1,
        distance: data.distance ?? 100,
        color: data.color ?? "#999999",
    });
}

/**
 * 更新链接
 * @param {*} data 
 * @param {*} nodes 
 * @param {*} links 
 * @returns 
 */
function updateLinkFromOperation(data, nodes, links) {
    // 如果你的 link 没有单独的 id，就只能通过 source+target 查找
    // 这里假设 data.source, data.target, data.newValue, data.distance, data.color
    const nodeMap = new Map(nodes.map(n => [n.name, n]));
    const sourceNode = nodeMap.get(data.source);
    const targetNode = nodeMap.get(data.target);

    if (!sourceNode || !targetNode) return;

    const link = links.find(l => l.source === sourceNode && l.target === targetNode);
    if (link) {
        if (typeof data.newValue !== "undefined") {
            link.value = data.newValue;
        }
        if (typeof data.newDistance !== "undefined") {
            link.distance = data.newDistance;
        }
        if (typeof data.newColor !== "undefined") {
            link.color = data.newColor;
        }
    }
}

/**
 * 删除链接
 * @param {*} data 
 * @param {*} nodes 
 * @param {*} links 
 * @returns 
 */
function deleteLinkFromOperation(data, nodes, links) {
    const nodeMap = new Map(nodes.map(n => [n.name, n]));
    const sourceNode = nodeMap.get(data.source);
    const targetNode = nodeMap.get(data.target);
    if (!sourceNode || !targetNode) return;

    for (let i = links.length - 1; i >= 0; i--) {
        const l = links[i];
        if (l.source === sourceNode && l.target === targetNode) {
            links.splice(i, 1);
            break;  // 假设只删第一条匹配
        }
    }
}
