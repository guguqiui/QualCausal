import { v4 as uuidv4 } from 'uuid';

/**
 * 根据 instanceToSave 的 source 和 name，找到对应的节点对象，
 * 并将 sourceNode -> targetNode (value) 做自增或新建
 * @param {*} ctx 
 * @param {*} instanceToSave 
 * @returns 
 */
export function updateLinkWeight(ctx, instanceToSave) {
  // 1) 如果没有 source 或没有 name，直接跳过
  if (!instanceToSave.source || !instanceToSave.name) return;
  // 2) 找到 sourceNode 与 targetNode（即 instance 所属的 node）
  const sourceNode = ctx.nodes.find(n => n.name === instanceToSave.source);
  const targetNode = ctx.nodes.find(n => n.name === instanceToSave.name);
  if (!sourceNode || !targetNode) { return; }
  createOrAddLinkValue(ctx, sourceNode, targetNode, 1, 100, sourceNode.color || "#999999");
}

/**
 * 在 ctx.links 中找 sourceNode -> targetNode 的 link，如果存在就累加 value，否则新建。
 * 并记录 LINK_CREATE 或 LINK_UPDATE 到 ctx.userOperations
 * @param {*} ctx 
 * @param {*} sourceNode 
 * @param {*} targetNode 
 * @param {*} deltaValue 
 * @param {*} distance 
 * @param {*} color 
 * @returns 
 */
export async function createOrAddLinkValue(
  ctx,
  sourceNode,
  targetNode,
  deltaValue = 1,
  distance = 100,
  color = "#999999"
) {
  if (!sourceNode || !targetNode) return; // 安全判断

  // 1) 查找是否已有 link
  let link = ctx.links.find(
    l => l.source.name === sourceNode.name && l.target.name === targetNode.name
  );
  console.log("link:", link);

  if (!link) {
    // 2) 如果没有，创建新链接
    console.log("create link...")
    link = {
      tempId: uuidv4(),
      source: sourceNode,
      target: targetNode,
      value: deltaValue,
      distance,
      color
    };
    ctx.links.push(link);

    // 记录 LINK_CREATE
    const linkOpData = {
      tempId: link.tempId,
      source: sourceNode.name,
      target: targetNode.name,
      value: link.value,
      distance: link.distance,
      color: link.color,
    };
    const linkCreateOp = {
      userId: ctx.userId,
      operationType: "LINK_CREATE",
      operationData: JSON.stringify(linkOpData),
    };
    ctx.userOperations.push(linkCreateOp);
    ctx.isDirty = true;

  } else {
    console.log("update link: ", link)
    // 3) 如果找到，更新 link.value += deltaValue
    const oldValue = link.value;
    link.value += deltaValue;

    // 记录 LINK_UPDATE
    const linkOpData = {
      id: link.tempId || link.id,
      source: sourceNode,
      target: targetNode,
      oldValue,
      newValue: link.value,
      distance: link.distance,
      color: link.color,
    };
    const linkUpdateOp = {
      userId: ctx.userId,
      operationType: "LINK_UPDATE",
      operationData: JSON.stringify(linkOpData),
    };
    ctx.userOperations.push(linkUpdateOp);
    ctx.isDirty = true;
  }
  ctx.mainGroup.selectAll("*").remove();  // 清空旧图形
  ctx.renderGraph();                      // 重新绘制
}

/**
 * 删除 link，并记录 LINK_DELETE
 * @param {*} ctx 
 * @param {*} link 
 */
export async function deleteLink(ctx, link) {
  // 1) 从 ctx.links 中删除
  const index = ctx.links.indexOf(link);
  if (index !== -1) {
    ctx.links.splice(index, 1);

    if (link.id || link.tempId) {
      // 2) 记录 LINK_DELETE 操作
      const linkOpData = {
        id: link.id || link.tempId,
        source: link.source.name,
        target: link.target.name,
        value: link.value,
        distance: link.distance,
        color: link.color
      };
      const linkDelOp = {
        userId: ctx.userId,
        operationType: "LINK_DELETE",
        operationData: JSON.stringify(linkOpData),
      };
      ctx.userOperations.push(linkDelOp);
      ctx.isDirty = true;
    }
  }
}

/**
 * 在 ctx.links 中找 sourceNode -> targetNode 的 link，减少 link 的 value
 * @param {*} ctx 
 * @param {*} deletedInstance 
 */
export function reduceLinkValue(ctx, deletedInstance) {
  console.log("deletedInstance: ", deletedInstance);
  if (deletedInstance.source && deletedInstance.name) {
    const sourceNode = ctx.nodes.find(n => n.name === deletedInstance.source);
    const targetNode = ctx.nodes.find(n => n.name === deletedInstance.name);

    if (sourceNode && targetNode) {
      let link = ctx.links.find(
        l => l.source.name === sourceNode.name && l.target.name === targetNode.name
      );
      if (link) {
        const oldValue = link.value;
        link.value -= 1;
        if (link.value > 0) {   // 记录 LINK_UPDATE
          recordLinkUpdate(ctx, sourceNode, targetNode, link, oldValue);
        } else {    // 如果 value <= 0 则删除这条边
          console.log("delete link: ", link)
          deleteLink(ctx, link);
        }
      }
    }
  }
}

/**
 * 记录操作
 * @param {*} ctx 
 * @param {*} sourceNode 
 * @param {*} targetNode 
 * @param {*} link 
 * @param {*} oldValue 
 */
function recordLinkUpdate(ctx, sourceNode, targetNode, link, oldValue) {
  const linkOpData = {
    id: link.tempId || link.id,
    source: sourceNode,
    target: targetNode,
    oldValue,
    newValue: link.value,
    distance: link.distance,
    color: link.color,
  };

  const linkUpdateOp = {
    userId: ctx.userId,
    operationType: "LINK_UPDATE",
    operationData: JSON.stringify(linkOpData),
  };

  ctx.userOperations.push(linkUpdateOp);
  ctx.isDirty = true;
}