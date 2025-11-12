
import { useApp } from '@/contexts/AppContext';
import LeftSidebar from '@/components/LeftSidebar';
import SettingsModal from '@/components/SettingsModal';
import AdvancedSettingsModal from '@/components/AdvancedSettingsModal';
import PaymentModal from '@/components/PaymentModal';
import MyAccountModal from '@/components/MyAccountModal';

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
      {/* 대화 목록 사이드바 */}
      <LeftSidebar
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

      {/* 마이 어카운트 모달 */}
      <MyAccountModal />
    </>
  );
}
