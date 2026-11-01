import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { OverviewPage }     from './pages/OverviewPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { CodeGraphPage }    from './pages/CodeGraphPage';
import { TraversalPage }    from './pages/TraversalPage';
import { RetrievalPage }    from './pages/RetrievalPage';
import { ContextPage }      from './pages/ContextPage';
import { AgentPage }        from './pages/AgentPage';
import { SettingsPage }     from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/"            element={<OverviewPage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/graph"        element={<CodeGraphPage />} />
            <Route path="/traversal"    element={<TraversalPage />} />
            <Route path="/retrieval"    element={<RetrievalPage />} />
            <Route path="/context"      element={<ContextPage />} />
            <Route path="/agent"        element={<AgentPage />} />
            <Route path="/settings"     element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
