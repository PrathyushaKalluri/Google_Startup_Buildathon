import { useStore } from './store';
import { Layout, Toasts } from './components/Layout';
import { Panels } from './components/Panels';
import { AssetDrawer } from './components/AssetDrawer';
import { ProviderDrawer } from './components/ProviderDrawer';
import { AddMemoryModal, SourceModal } from './components/Memory';
import { Home } from './screens/Home';
import { Memory } from './screens/Memory';
import { Work } from './screens/Work';
import { Calendar } from './screens/Calendar';
import { Providers } from './screens/Providers';

export default function App() {
  const { route } = useStore();
  return (
    <>
      <Layout>
        {route.screen === 'home' && <Home />}
        {route.screen === 'memory' && <Memory />}
        {route.screen === 'work' && <Work />}
        {route.screen === 'calendar' && <Calendar />}
        {route.screen === 'providers' && <Providers />}
      </Layout>
      <Panels />
      <AssetDrawer />
      <ProviderDrawer />
      <AddMemoryModal />
      <SourceModal />
      <Toasts />
    </>
  );
}
