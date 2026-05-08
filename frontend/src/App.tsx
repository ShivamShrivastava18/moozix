import { Route, Routes } from "react-router-dom";

import { TopNav } from "./components/TopNav";
import { useAuthStatus } from "./hooks/useAuthStatus";
import { ComparePage } from "./pages/ComparePage";
import { LandingPage } from "./pages/LandingPage";
import { MePage } from "./pages/MePage";
import { PostLoginPage } from "./pages/PostLoginPage";

export default function App() {
  const { data: status } = useAuthStatus();
  return (
    <>
      <TopNav
        authenticated={status?.authenticated ?? false}
        user={status?.user ?? null}
      />
      <main>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/post-login" element={<PostLoginPage />} />
          <Route path="/me" element={<MePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/compare/:userB" element={<ComparePage />} />
        </Routes>
      </main>
    </>
  );
}
