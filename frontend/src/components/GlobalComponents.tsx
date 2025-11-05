
import { useApp } from '@/contexts/AppContext';
import SettingsSidebar from '@/components/SettingsSidebar';
import SettingsModal from '@/components/SettingsModal';
import AdvancedSettingsModal from '@/components/AdvancedSettingsModal';
import PaymentModal from '@/components/PaymentModal';

export default function GlobalComponents() {
  const {
    isSidebarOpen,
    isSettingsModalOpen,
    isAdvancedSettingsOpen,
    isPaymentModalOpen,
    closeSidebar,
    closeSettings,
    closeAdvancedSettings,
    closePaymentModal
  } = useApp();

  return (
    <>
      {/* 전역 사이드바 */}
      <SettingsSidebar
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
      />

      {/* 기본 설정 모달 */}
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={closeSettings}
      />

      {/* 고급 설정 모달 */}
      <AdvancedSettingsModal
        isOpen={isAdvancedSettingsOpen}
        onClose={closeAdvancedSettings}
      />

      {/* 결제 모달 */}
      <PaymentModal
        isOpen={isPaymentModalOpen}
        onClose={closePaymentModal}
      />
    </>
  );
}