import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',               name: 'home',           component: () => import('../pages/home/views/HomeView.vue') },
  { path: '/chat',           name: 'chat',           component: () => import('../pages/chat/views/ChatView.vue') },
  { path: '/knowledge-base', name: 'knowledge-base', component: () => import('../pages/knowledge-base/views/KnowledgeBaseView.vue') },
  { path: '/configuration',  name: 'configuration',  component: () => import('../pages/configuration/views/ConfigView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
