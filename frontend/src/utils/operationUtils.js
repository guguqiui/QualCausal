import { 
  createNodeAPI, updateNodeAPI, deleteNodeAPI, 
  createLinkAPI, updateLinkAPI, deleteLinkAPI, 
  createInstanceAPI, updateInstanceAPI, deleteInstanceAPI } from "@/api/api";
import * as d3 from 'd3';

/**
 * 辅助函数：根据传入的节点信息（可能为字符串或对象），返回真实的节点 id
 * @param {*} ctx 上下文对象
 * @param {*} nodeOrKey 节点信息（可能是临时 id、节点名称或节点对象）
 * @param {*} tempIdMapping 临时 id 到真实 id 的映射对象
 * @returns {number|string} 节点的真实 id，如果查不到则返回原值
 */
function getRealNodeId(ctx, nodeOrKey, tempIdMapping) {
  // 如果传入的是对象
  if (typeof nodeOrKey === 'object' && nodeOrKey !== null) {
    // 如果对象已有 id，则直接返回
    if (nodeOrKey.id) {
      return nodeOrKey.id;
    }
    // 如果对象中有 tempId，并且映射中存在，则返回映射中的 id
    if (nodeOrKey.tempId && tempIdMapping[nodeOrKey.tempId]) {
      return tempIdMapping[nodeOrKey.tempId];
    }
    // 尝试根据 name 在 ctx.nodes 中查找（注意：name 应该唯一，否则需调整逻辑）
    const found = ctx.nodes.find(n => n.name === nodeOrKey.name);
    return found && found.id ? found.id : null;
  }
  // 如果传入的是字符串，则依次尝试从映射或 ctx.nodes 中查找
  const idFromMapping = tempIdMapping[nodeOrKey];
  if (idFromMapping) return idFromMapping;

  const idFromTempId = ctx.nodes.find(n => n.tempId === nodeOrKey)?.id;
  if (idFromTempId) return idFromTempId;

  const idFromName = ctx.nodes.find(n => n.name === nodeOrKey)?.id;
  if (idFromName) return idFromName;

  // 3. 如果所有查找都失败，则返回 null，而不是原始值
  console.warn(`[getRealNodeId] 未找到有效的 ID:`, nodeOrKey);
  return null;
}

function getRealNode(ctx, nodeOrKey, tempIdMapping) {
  // 如果传入的是对象
  if (typeof nodeOrKey === 'object' && nodeOrKey !== null) {
    // 如果对象已有 id，则直接返回完整对象
    if (nodeOrKey.id) {
      return nodeOrKey;
    }
    // 如果对象中有 tempId，并且映射中存在，则返回映射中的对象
    if (nodeOrKey.tempId && tempIdMapping[nodeOrKey.tempId]) {
      return ctx.nodes.find(n => n.id === tempIdMapping[nodeOrKey.tempId]) || null;
    }
    // 尝试根据 name 在 ctx.nodes 中查找（注意：name 应该唯一，否则需调整逻辑）
    return ctx.nodes.find(n => n.name === nodeOrKey.name) || null;
  }

  // 如果传入的是字符串，则依次尝试从映射或 ctx.nodes 中查找
  const idFromMapping = tempIdMapping[nodeOrKey];
  if (idFromMapping) {
    return ctx.nodes.find(n => n.id === idFromMapping) || null;
  }

  const nodeFromTempId = ctx.nodes.find(n => n.tempId === nodeOrKey);
  if (nodeFromTempId) return nodeFromTempId;

  const nodeFromName = ctx.nodes.find(n => n.name === nodeOrKey);
  if (nodeFromName) return nodeFromName;

  // 如果所有查找都失败，则返回 null，而不是原始值
  console.warn(`[getRealNode] 未找到有效的 Node:`, nodeOrKey);
  return null;
}


/**
 * 取消编辑
 * @param {*} ctx
 */
export function cancelEdit(ctx) {
  // 1. 恢复 Instances
  ctx.selectedInstances = JSON.parse(JSON.stringify(ctx.originalInstances));
  ctx.selectedInstances = ctx.selectedInstances.filter(instance => !instance.isNew);

  // 2. 确保 currentIndex 在有效范围内
  if (ctx.currentIndex >= ctx.selectedInstances.length) {
    ctx.currentIndex = ctx.selectedInstances.length > 0 ? ctx.selectedInstances.length - 1 : 0;
  }

  // 3. 如果恢复后没有实例了，则隐藏右侧展示框
  if (ctx.selectedInstances.length === 0) {
    ctx.isInstanceContentVisible = false;
  }

  // 4. 如果这是“新增节点模式”下的取消，就删除新建节点
  if (ctx.isNodeEditMode) {
    const nodeObject = ctx.nodes.find(n => n.name === ctx.selectedNodeName);  // 找到当前节点
    if (nodeObject) {
      const index = ctx.nodes.findIndex(n => n.name === nodeObject.name); // 从 nodes 中移除
      if (index !== -1) {
        ctx.nodes.splice(index, 1);
      }
      ctx.links = ctx.links.filter( // 从 links 中移除相关边
        l => l.source.name !== nodeObject.name && l.target.name !== nodeObject.name
      );
    }
  }
  ctx.isAddingNewNode = false;
  ctx.isEditMode = false;
  ctx.isNodeEditMode = false;
  ctx.mainGroup.selectAll("*").remove();
  ctx.renderGraph();
}



/**
 * 撤销操作
 * @param {*} ctx
 */
export function undoOperation(ctx) {
  if (ctx.undoStack.length > 0) {
    const prevState = ctx.undoStack.pop();
    ctx.thirdElementToInstances = prevState.thirdElementToInstances;
    ctx.selectedInstances = prevState.selectedInstances;
    ctx.selectedNodeName = prevState.selectedNodeName;
    ctx.nodes = prevState.nodes;
    ctx.links = fixLinkReferences(ctx.nodes, prevState.links);
    ctx.isInstanceContentVisible = prevState.isInstanceContentVisible;

    if (Array.isArray(ctx.selectedInstances)) {
      ctx.selectedInstances.forEach(instance => {
        if (instance) { // 确保 instance 不为 undefined
          instance.editableName = false;
        }
      });
    }
    ctx.mainGroup.selectAll("*").remove();
    ctx.renderGraph();
  } else {
    console.log("No actions to undo");
  }
}

/**
 * 保存当前所有操作
 * 注意：首先处理 NODE_CREATE 和 INSTANCE_CREATE 操作建立 tempIdMapping，然后再处理 LINK_CREATE 等操作，
 * 确保传给 createLinkAPI 的 source 和 target 均为正确的持久化 id（数字）。
 * @param {*} ctx
 * @param {*} axios
 * @param {*} config
 */
export async function saveAllOperations(ctx, axios, config) {
  if (ctx.userOperations.length === 0) {
    console.log("No operations to save");
    return;
  }

  // 用来存储 (tempId -> realId) 的映射
  if (!ctx.tempIdMapping) {
    ctx.tempIdMapping = {};  // 只初始化一次
  }
  const tempIdMapping = ctx.tempIdMapping;

  // const data = JSON.parse(op.operationData);
  let nodeCreateId = 0;

  try {
    const response = await axios.post(`${config.baseURL}/api/operations/batch`, ctx.userOperations);
    console.log("All operations saved successfully", response.data);

    // -------------------- 处理 NODE_CREATE --------------------
    for (let op of ctx.userOperations) {
      const data = JSON.parse(op.operationData);
      switch (op.operationType) {
        case "NODE_CREATE": {
          const created = await createNodeAPI(op.userId, {
            name: data.nodeName,
            type: data.type,
            color: data.color,
            weight: data.weight,
            source: data.source,
            isThirdElement: data.isThirdElement,
            x: data.x,
            y: data.y,
          });

          console.log("[saveAllOperations] NODE_CREATE 返回结果:", created);
          // 建立临时 id 与真实 id 的映射
          tempIdMapping[data.tempId] = created.id;
          console.log("node: data.tempId: ", data.tempId);
          console.log("tempIdMapping: ", tempIdMapping);

          //通过id找不到node，通过name找node会有什么风险吗？
          const localNode = ctx.nodes.find(n => n.name === data.nodeName);

          if (localNode) {
            localNode.id = created.id;
            nodeCreateId = localNode.id;
          }

          break;
        }
    // }

    // -------------------- 处理 INSTANCE_CREATE --------------------
        case "INSTANCE_CREATE": {
          const createdInst = await createInstanceAPI(op.userId, {
            category_: data.category_,
            attribution_type_: data.attribution_type_,
            question: data.question,
            opinion: data.opinion,
            name: data.name,
            source: data.source,
            type: data.type,
          });

          console.log("[saveAllOperations] INSTANCE_CREATE 返回:", createdInst);
          tempIdMapping[data.tempId] = createdInst.id;
          console.log("instance: data.tempId: ", data.tempId);
          console.log("tempIdMapping: ", tempIdMapping);

          // 更新本地实例的 id
          let localInst = findLocalInstance(ctx, data.tempId);
          if (localInst) {
            localInst.id = createdInst.id;
          }
          break;
        }

    // -------------------- 处理 LINK_CREATE --------------------
        case "LINK_CREATE": {
          console.log("LINK_CREATE data:", data)
          const realSource = getRealNode(ctx, data.source, tempIdMapping);
          const realTarget = getRealNode(ctx, data.target, tempIdMapping);

          // 传递node对象给后端接口
          const createdLink = await createLinkAPI(op.userId, {
            source: realSource,
            target: realTarget,
            value: data.value,
            distance: data.distance,
            color: data.color,
          });

          console.log("[saveAllOperations] LINK_CREATE 返回结果:", createdLink);

          if (data.tempId) {
            tempIdMapping[data.tempId] = createdLink.id;
          }
  
          // 更新本地链接对象中对应的 id
          const localLink = ctx.links.find(l => {
            const lSourceId = getRealNodeId(ctx, l.source, tempIdMapping);
            const lTargetId = getRealNodeId(ctx, l.target, tempIdMapping);
            return lSourceId === realSource.id && lTargetId === realTarget.id;
          });
          if (localLink) {
            localLink.id = createdLink.id;
          }
          break;
        }
    // }

    // -------------------- 处理其他操作 --------------------
        case "NODE_UPDATE": {

          //拿到的是instance ID，但其实我们想要的是node ID
          let realId = data.nodeId ?? tempIdMapping[data.nodeId]; // 假设这里拿到的是 nodeId，但不确定是不是tempId

          //如果这里是从"NODE_CREATE"等一系列操作过来的
          const hasNodeCreate = ctx.userOperations.some(op => op.operationType === "NODE_CREATE");

          if (hasNodeCreate) {
            realId = nodeCreateId;
            console.log("NODE_CREATE realId", realId);
          }

          const currentNode = ctx.nodes.find(n => n.id === realId);
          const updatedNode = { ...currentNode, ...data.updatedFields };
          console.log("NODE_UPDATE realId:", realId, "op.userId", op.userId, "data.updatedFields", data.updatedFields, "currentNode", currentNode, "updatedNode", updatedNode);
          await updateNodeAPI(op.userId, realId, updatedNode);
          console.log("[saveAllOperations] NODE_UPDATE 完成");
          break;
        }

        case "NODE_DELETE": {
          console.log("node delete data: ", data)
          console.log("tempIdMapping: ", tempIdMapping)
          const nodeId = tempIdMapping[data.nodeId] || data.nodeId;
          if(nodeId) {
            await deleteNodeAPI(op.userId, nodeId);
            console.log("[saveAllOperations] NODE_DELETE 完成");
          }
          break;
        }

        case "LINK_UPDATE": {
          console.log("data: ", data);
          // const realSourceId = getRealNodeId(ctx, data.source, tempIdMapping);
          // const realTargetId = getRealNodeId(ctx, data.target, tempIdMapping);
          // const localLink = ctx.links.find(l => {
          //   const lSourceId = getRealNodeId(ctx, l.source, tempIdMapping);
          //   const lTargetId = getRealNodeId(ctx, l.target, tempIdMapping);
          //   return lSourceId === realSourceId && lTargetId === realTargetId;
          // });
          const realLinkId = tempIdMapping[data.id] || data.id;
          if (!realLinkId) {
            console.warn("[saveAllOperations] LINK_UPDATE 失败，未找到 linkId", realLinkId);
            break;
          }

          const realSource = getRealNode(ctx, data.source, tempIdMapping);
          const realTarget = getRealNode(ctx, data.target, tempIdMapping);
          if (realLinkId) {
            await updateLinkAPI(op.userId, realLinkId, {
              source: realSource,
              target: realTarget,
              value: data.newValue,
              distance: data.distance,
              color: data.color,
            });
            console.log("[saveAllOperations] LINK_UPDATE 完成");
          } else {
            console.error("[saveAllOperations] LINK_UPDATE 失败，未找到 linkId");
          }
          break;
        }

        case "LINK_DELETE": {
          console.log("data: ", data);
          // const realSourceId = getRealNodeId(ctx, data.source, tempIdMapping);
          // const realTargetId = getRealNodeId(ctx, data.target, tempIdMapping);
          // const localLink = ctx.links.find(l => {
          //   const lSourceId = getRealNodeId(ctx, l.source, tempIdMapping);
          //   const lTargetId = getRealNodeId(ctx, l.target, tempIdMapping);
          //   return lSourceId === realSourceId && lTargetId === realTargetId;
          // });
          const realLinkId = tempIdMapping[data.id] || data.id;
          if (!realLinkId) {
            console.warn("[saveAllOperations] LINK_DELETE 失败，未找到 linkId", realLinkId);
            break;
          }
          try {
            await deleteLinkAPI(op.userId, realLinkId);
            console.log("[saveAllOperations] LINK_DELETE 成功:", realLinkId);
            ctx.links = ctx.links.filter(l => l.id !== realLinkId);
          } catch (err) {
            console.error("[saveAllOperations] LINK_DELETE 失败:", err);
          }
          break;
        }

        case "INSTANCE_UPDATE": {
          const realInstId = tempIdMapping[data.instanceId] || data.instanceId;
          await updateInstanceAPI(op.userId, realInstId, data.updatedFields);
          console.log("[saveAllOperations] INSTANCE_UPDATE 完成");
          break;
        }
        case "INSTANCE_DELETE": {
          const instId = tempIdMapping[data.instanceId] || data.instanceId;
          console.log("test: ", data.instanceId, instId);
          console.log("[DEBUG] data.instanceId:", data.instanceId, "类型:", typeof data.instanceId);
          console.log("[DEBUG] tempIdMapping:", tempIdMapping);
          await deleteInstanceAPI(op.userId, instId);
          console.log("[saveAllOperations] INSTANCE_DELETE 完成");
          break;
        }
        default:
          console.warn("[saveAllOperations] 未知的操作类型:", op.operationType);
          break;
      }
    }

    // 清空操作记录，并标记数据为最新
    ctx.userOperations = [];
    ctx.isDirty = false;

    ctx.mainGroup.selectAll("*").remove(); 
    await ctx.fetchGraphData();
    alert("Save successful!");
    console.log("Graph data refreshed after saving.");
    ctx.svg.transition().duration(500).call(
      ctx.zoom.transform,
      d3.zoomIdentity.translate(ctx.initialX, ctx.initialY).scale(0.4)
    );
  } catch (error) {
    console.error("Failed to save all operations:", error);
  }
}


/**
 * 展示下拉框
 */
export function showInstanceContent() {
  const instanceContent = document.querySelector('.instance-content');
  if (instanceContent) {
    instanceContent.style.transition = 'none';
    instanceContent.style.transform = 'translateY(-150%)';
    void instanceContent.offsetHeight; // 触发重绘
    instanceContent.style.transition = "transform 0.5s ease";
    instanceContent.style.transform = "translateY(0)";
  }
}

/**
 * 校验新节点
 * @param {*} ctx 
 * @param {*} instanceToSave 
 * @returns 
 */
export function validateNodeAndInstance(ctx, instanceToSave) {
  ctx.validationErrors = {}; // 重置错误信息
  // 1. 校验名称是否为空
  if (!instanceToSave.name || instanceToSave.name.trim() === "") {
    ctx.validationErrors.name = "Name cannot be empty.";
  }
  // 2. 校验 Category 是否为空
  if (!instanceToSave.category_ || instanceToSave.category_.trim() === "") {
    ctx.validationErrors.category = "Category cannot be empty.";
  }
  // 3. 校验 Attribution 是否为空
  if (!instanceToSave.attribution_type_ || instanceToSave.attribution_type_.trim() === "") {
    ctx.validationErrors.attribution = "Attribution cannot be empty.";
  }
  // 4. 校验 Type 是否为空
  if (!instanceToSave.type || instanceToSave.type.trim() === "") {
    ctx.validationErrors.type = "Type cannot be empty.";
  } 
  // 5. 校验 Interview 是否为空
  if (!instanceToSave.question || instanceToSave.question.trim() === "") {
    ctx.validationErrors.question = "Interview cannot be empty.";
  } 
  // 6. 校验 Panticipant 是否为空
  if (!instanceToSave.opinion || instanceToSave.opinion.trim() === "") {
    ctx.validationErrors.opinion = "Panticipant cannot be empty.";
  } 

  // 如果到这里已经有错误了，就直接 return，不用再做重复性校验
  if (Object.keys(ctx.validationErrors).length > 0) {
    return;
  }

  // 7. 进行“所有字段都相同”的重复检查
  const allInstances = Object.values(ctx.thirdElementToInstances || {}).flat();
  // 在 allInstances 中找有没有“与当前要保存的 instanceToSave 完全一致”的实例
  const foundDuplicate = allInstances.find(inst =>
    // 不是同一个对象本身（如果你允许修改已有实例，就要排除它自己）
    inst !== instanceToSave &&
    inst.name === instanceToSave.name &&
    inst.category_ === instanceToSave.category_ &&
    inst.attribution_type_ === instanceToSave.attribution_type_ &&
    inst.type === instanceToSave.type &&
    inst.question === instanceToSave.question &&
    inst.opinion === instanceToSave.opinion
  );

  if (foundDuplicate) {
    ctx.validationErrors.duplicate = "An identical instance already exists. Please modify it.";
  }
}

/**
 * 如果当前上下文中有正在添加的新节点（还没确认），就阻止继续操作。
 * @param {*} ctx
 * @returns {boolean} true=已阻止操作，false=允许继续
 */
export function blockIfPendingNewNode(ctx) {
  if (ctx.isAddingNewNode) {
    console.warn("There is a new node pending confirmation. Please confirm (or cancel) it before proceeding.");
    return true;
  }
  return false;
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

/**
 * 在 ctx.thirdElementToInstances 里查找本地的 Instance
 * @param {Object} ctx - 上下文对象
 * @param {string} tempId - 临时 ID（如果实例还没有真实 ID）
 * @returns {Object|null} 找到的实例对象，或 null（如果没找到）
 */
export function findLocalInstance(ctx, tempId) {
  for (const nodeName in ctx.thirdElementToInstances) {
    const instances = ctx.thirdElementToInstances[nodeName];

    const foundInstance = instances.find(inst => inst.tempId === tempId || inst.id === tempId);
    if (foundInstance) {
      return foundInstance;
    }
  }
  return null;
}