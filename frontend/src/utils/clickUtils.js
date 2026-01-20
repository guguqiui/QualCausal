import * as d3 from 'd3';

export function handleNodeClick(context, event, d) {
  if (context.categoryOptions.includes(d.name)) {
    return;
  }

  // 暂停力导向图模拟
  context.pauseSimulation();

  // 固定节点位置
  context.fixNodePosition(d);

  const instances = context.thirdElementToInstances?.[d.name];
  if (instances && instances.length > 0 && d.name !== 'anger') {
    context.selectedNodeName = d.name;
    context.selectedInstances = instances.map(instance => ({ ...instance }));
    context.currentIndex = 0;
  } else if (!context.attributionOptions.includes(d.name) && !context.categoryOptions.includes(d.name)) {
    context.selectedNodeName = d.name;
    context.selectedInstances = instances ? instances.map(i => ({ ...i })) : [];
    context.currentIndex = 0;
  } else if (context.attributionOptions.includes(d.name)) {
    context.selectedNodeName = d.name;
    context.selectedInstances = [];
    context.isInstanceContentVisible = false;
  } else {
    // 这里也要把 selectedInstances = []（或空），并把 isInstanceContentVisible = true
    // 这样即使没有实例，也可以让下拉框出现
    context.selectedNodeName = d.name;
    context.selectedInstances = instances || [];
    context.isInstanceContentVisible = true;
    context.currentIndex = 0;
  }

  // zoomToNode(context, d);

  d3.selectAll('.radial-menu').remove();

  zoomToNode(context, d, 5);

  setTimeout(() => {
    renderRadialMenu(context, d);
  }, 800);

  event.stopPropagation();
}

function renderRadialMenu(context, d) {
  const radius = d.size;
  const numArcs = 4;
  const colors = ["#BBE7FE", "#D3B5E5", "#FFD4DB", "#EFF1DB"];
  const icons = [
    require('@/assets/add.svg'),
    require('@/assets/delete.svg'),
    require('@/assets/revise.svg'),
    require('@/assets/detail.svg')
  ];

  const isAttribution = context.attributionOptions.includes(d.name);
  
  const arcGenerator = d3.arc()
    .innerRadius(radius)
    .outerRadius(isAttribution ? radius + 20 : radius + 10);

  const arcData = d3.range(numArcs).map(i => ({
    startAngle: (i * 2 * Math.PI) / numArcs,
    endAngle: ((i + 1) * 2 * Math.PI) / numArcs,
    index: i
  }));

  const menuGroup = context.mainGroup.append('g')
    .attr('class', 'radial-menu')
    .attr('transform', `translate(${d.x}, ${d.y})`);

  menuGroup.selectAll('.menu-arc')
    .data(arcData)
    .enter()
    .append('path')
    .attr('class', 'menu-arc')
    .attr('d', arcGenerator)
    .attr('fill', (d) => {
      return colors[d.index];
    })
    .style('fill-opacity', 1)
    .style('cursor', 'pointer')
    .on('click', (event) => {
      event.stopPropagation();
    });

  menuGroup.selectAll('.menu-icon')
    .data(arcData)
    .enter()
    .append('image')
    .attr('class', 'menu-icon')
    .attr('xlink:href', (d) => icons[d.index])
    .attr('width', 10)
    .attr('height', 10)
    .attr('x', (d) => {
      const [x] = arcGenerator.centroid(d);
      return x - 5;
    })
    .attr('y', (d) => {
      const [, y] = arcGenerator.centroid(d);
      return y - 5;
    })
    .on('click', (evt, arcD) => {
      evt.stopPropagation();
      d3.selectAll('.radial-menu').remove();

      const opIndex = arcD.index;
      const isAttribution = context.attributionOptions.includes(d.name);
      const isThirdElement = (!isAttribution && d.name !== 'stigma' && d.name !== 'no stigma');

      if (isAttribution) {
        if (opIndex === 3) {

          const navigate = confirm("Do you want to navigate to the detail view?");
          if (navigate) {
            if (context.isDirty) {
              const userConfirmed = window.confirm("You have unsaved changes. Do you really want to leave?");
              // 用户点击“取消”就停止导航
              if (!userConfirmed) {
                return;
              }
            }
            context.$router.push({ 
              name: 'DetailView', 
              query: { 
                id: d.name,
                userId: context.userId
              }
            });
          }
        } else if (opIndex === 0) {
          context.clickedNodeName = d.name;
          context.addNewNode();
          context.isInstanceContentVisible = true;
        } else if (opIndex === 1) {
          alert("Cannot delete attribution nodes.");
        } else if (opIndex === 2) {
          alert("Cannot revise attribution nodes.");
        }

        // 恢复力导向图模拟并释放节点位置
        context.resumeSimulation();
        context.releaseNodePosition(d);
      } else if (isThirdElement) {
        if (opIndex === 3) {
          context.isInstanceContentVisible = true;
          context.$nextTick(() => {
            context.showInstanceContent();
          });
        } else if (opIndex === 0) {
          context.clickedNodeName = d.name;
          context.addNewNode();
          context.isInstanceContentVisible = true;
          zoomToNode(context, d, 1.5);
        } else if (opIndex === 1) {
          context.deleteNode(d.name);
        } else if (opIndex === 2) {
          context.EditInstance();
          context.isEditMode = true;
          context.isInstanceContentVisible = true;
        }

        // 恢复力导向图模拟并释放节点位置
        context.resumeSimulation();
        context.releaseNodePosition(d);
      }
    });

  d3.select('body').on('click', () => {
    d3.selectAll('.radial-menu').remove();

    // 恢复力导向图模拟并释放节点位置
    context.resumeSimulation();
    context.releaseNodePosition(d);
  });
  // event.stopPropagation();
}

export function zoomToNode(context, d, scaleFactor) {
  const svg = context.svg;       // 你在初始化时存的
  const zoom = context.zoom;     // 你在初始化时存的
  const width = context.width;
  const height = context.height;

  if(context.attributionOptions.includes(d.name)) {
    scaleFactor = 1.5;
  }
  
  // 节点坐标 d.x, d.y (在 mainGroup 的坐标系中)
  // 目标：把 d.x,d.y 移到画布中心 (width/2, height/2)
  // transform = translate(width/2, height/2) → scale(scale) → translate(-d.x, -d.y)
  const transform = d3.zoomIdentity
    .translate(width / 2.5, height / 2)
    .scale(scaleFactor)
    .translate(-d.x, -d.y);

  // 使用 transition 平滑移动
  svg.transition()
    .duration(750)
    .call(zoom.transform, transform)
    .on('end', () => {
      // console.log('Zoom completed for node:', d.name);
    });
}