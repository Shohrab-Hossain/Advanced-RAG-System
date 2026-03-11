import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',               name: 'home',           component: () => import('../views/HomeView.vue') },
  { path: '/chat',           name: 'chat',           component: () => import('../views/ChatView.vue') },
  { path: '/knowledge-base', name: 'knowledge-base', component: () => import('../views/KnowledgeBaseView.vue') },
  { path: '/configuration',  name: 'configuration',  component: () => import('../views/ConfigView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
