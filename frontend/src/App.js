import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import PortalLayout from "@/components/PortalLayout";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Dashboard from "@/pages/Dashboard";
import CoursesPage from "@/pages/Courses";
import CourseDetail from "@/pages/CourseDetail";
import LessonPage from "@/pages/LessonPage";
import RecordingPage from "@/pages/RecordingPage";
import AttendancePage from "@/pages/AttendancePage";
import LiveClasses from "@/pages/LiveClasses";
import TestsPage from "@/pages/Tests";
import TakeTest from "@/pages/TakeTest";
import TestBuilder from "@/pages/TestBuilder";
import TestResults from "@/pages/TestResults";
import TestReview from "@/pages/TestReview";
import Certificate from "@/pages/Certificate";
import Leaderboard from "@/pages/Leaderboard";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import AssignmentsPage from "@/pages/Assignments";
import AnnouncementsPage from "@/pages/Announcements";
import AdminUsers from "@/pages/AdminUsers";
import AdminPayments from "@/pages/AdminPayments";
import AdminTeachers from "@/pages/AdminTeachers";
import AdminTopPerformers from "@/pages/AdminTopPerformers";
import AdminSettings from "@/pages/AdminSettings";
import AdminEnrollments from "@/pages/AdminEnrollments";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500" data-testid="app-loading">
        Loading…
      </div>
    );
  if (!user) return <Navigate to="/auth?mode=login" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route
            path="/certificate/:courseId"
            element={
              <Protected>
                <Certificate />
              </Protected>
            }
          />
          <Route
            path="/app"
            element={
              <Protected>
                <PortalLayout />
              </Protected>
            }
          >
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="courses" element={<CoursesPage />} />
            <Route path="courses/:id" element={<CourseDetail />} />
            <Route path="courses/:courseId/lessons/:lessonId" element={<LessonPage />} />
            <Route path="live" element={<LiveClasses />} />
            <Route path="live/:id/recording" element={<RecordingPage />} />
            <Route path="live/:id/attendance" element={<AttendancePage />} />
            <Route path="tests" element={<TestsPage />} />
            <Route path="tests/new" element={<TestBuilder />} />
            <Route path="tests/:id/edit" element={<TestBuilder />} />
            <Route path="tests/:id/take" element={<TakeTest />} />
            <Route path="tests/:id/results" element={<TestResults />} />
            <Route path="tests/:id/review" element={<TestReview />} />
            <Route path="tests/:id/leaderboard" element={<Leaderboard />} />
            <Route path="assignments" element={<AssignmentsPage />} />
            <Route path="announcements" element={<AnnouncementsPage />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="payments" element={<AdminPayments />} />
            <Route path="teachers" element={<AdminTeachers />} />
            <Route path="top-performers" element={<AdminTopPerformers />} />
            <Route path="settings" element={<AdminSettings />} />
            <Route path="enrollments" element={<AdminEnrollments />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
