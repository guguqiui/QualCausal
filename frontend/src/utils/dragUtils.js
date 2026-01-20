/**
 * 开始拖动
 * @param {*} event 
 * @param {*} d 
 * @param {*} simulation 
 */
export function dragStarted(event, d, simulation) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

/**
 * 拖动
 * @param {*} event 
 * @param {*} d 
 */
export function dragged(event, d) {
  clearTimeout(this.dragTimeout); // 如果您在组件中有dragTimeout，也需要通过参数传入
  d.fx = event.x;
  d.fy = event.y;
}

/**
 * 结束拖动
 * @param {*} event 
 * @param {*} d 
 * @param {*} simulation 
 */
export function dragEnded(event, d, simulation) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}