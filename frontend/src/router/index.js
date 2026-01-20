// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import UserLogin from '../components/User-login.vue'
import Main from '../components/Main.vue'
import DetailView from '../components/Detail-view.vue'
import NodeView from '../components/Node-view.vue'
import IntroView from '../components/Intro-view.vue'
import UploadView from '../components/Upload-view.vue'
import DrawingBoard from '../components/Drawing-board.vue'
import SelectedView from '../components/Selected-view.vue'
import TheoryView from '@/components/Theory-view.vue'

const routes = [
  { path: '/', 
    name: 'UserLogin', 
    component: UserLogin 
  },
  {
    path: '/upload',
    name: 'UploadView',
    component: UploadView
  },
  {
    path: '/drawing',
    name: 'DrawingBoard',
    component: DrawingBoard
  },
  {
    path: '/intro-view',
    name: 'IntroView',
    component: IntroView
  },
  {
    path: '/main',  // 根路径
    name: 'Main',
    component: Main
  },
  {
    path: '/detail-view',  // 详情页面路径
    name: 'DetailView',
    component: DetailView
  },
  {
    path: '/selected-view',  // 详情页面路径
    name: 'SelectedView',
    component: SelectedView
  },
  {
    path: '/node-view',
    name: 'NodeView',
    component: NodeView
  },
  {
    path: '/theory-view',
    name: 'TheoryView',
    component: TheoryView
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router