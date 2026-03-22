# Handoff: Фазы 6-7

## Статус: Завершено

## Фаза 6: Frontend и визуализация

### Что реализовано

#### Технологический стек
- React 19 + TypeScript
- Vite (сборка)
- React Router (маршрутизация)
- TanStack Query (серверный state)
- Zustand (UI state / фильтры)
- Axios (HTTP client)
- Cytoscape.js (визуализация графа)
- MUI 6 (UI библиотека)

#### Компоненты
| Компонент | Файл | Описание |
|---|---|---|
| Layout | `components/Layout.tsx` | Основной layout с боковым чатом |
| SearchChatPanel | `components/SearchChatPanel.tsx` | RAG чат-интерфейс |
| GraphView | `components/GraphView.tsx` | Cytoscape.js граф сущностей |
| ArticleList | `components/ArticleList.tsx` | Список статей с пагинацией |
| FilterPanel | `components/FilterPanel.tsx` | Фильтры (дата, источник, язык, сортировка) |
| ErrorBoundary | `components/ErrorBoundary.tsx` | Обработка ошибок React |

#### Страницы
| Страница | Маршрут | Описание |
|---|---|---|
| Dashboard | `/` | Граф + кластеры + список статей |
| Article Detail | `/articles/:id` | Полная статья + сущности + похожие |
| Entity Detail | `/entities/:name` | Сущность + граф + связанные статьи |
| Cluster Detail | `/clusters/:id` | Кластер + статьи в нём |

#### Backend API (расширено в фазе 6)
Новые endpoints:
- `GET /api/articles` — пагинация, фильтры (source, language, cluster_id, date_from, date_to, sort)
- `GET /api/articles/{id}` — детали статьи с сущностями и похожими статьями
- `GET /api/graph` — граф по article_id / entity_name / query (max 50 nodes, 80 edges)
- `GET /api/entities/{name}` — детали сущности

CORS: Добавлен `CORSMiddleware` для всех origins.

#### UX
- Loading skeletons при загрузке
- Пустые состояния с подсказками
- Degraded mode индикация от RAG
- Error boundary с кнопкой retry
- Responsive layout: desktop (sidebar chat) и mobile (drawer)

## Фаза 7: Интеграция и deploy

### Docker Compose
- Добавлен `frontend` сервис (nginx + static build)
- Nginx проксирует `/api/` на backend
- Frontend доступен на порту 3000

### Тестирование
- TypeScript: 0 ошибок
- Vite build: успешен
- Backend API: расширен и совместим

### Файлы фаз 6-7
```
frontend/
  src/
    api/client.ts
    store/useFilterStore.ts
    types/index.ts
    theme.ts
    components/{Layout,SearchChatPanel,GraphView,ArticleList,FilterPanel,ErrorBoundary}.tsx
    pages/{Dashboard,ArticleDetail,EntityDetail,ClusterDetail}.tsx
docker/
  frontend.Dockerfile
  nginx.conf
```

### Известные ограничения
- Качество NER и relations — MVP/baseline
- Clustering нестабилен на маленьком датасете
- Groq free-tier лимиты
- Граф ограничен 50 узлами / 80 связями
- Нет auth, нет real-time, нет streaming
