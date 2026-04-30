"use client";

import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { api, Appointment } from "@/lib/api";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function ConsultationContent() {
  const router = useRouter();
  const params = useSearchParams();
  const requestedAppointmentId = params.get("appointment_id");

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.appointments
      .list()
      .then((rows) => {
        setAppointments(
          rows
            .filter((row) => row.status !== "cancelled")
            .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
        );
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const selectedAppointment = useMemo(() => {
    if (!appointments.length) return null;
    if (requestedAppointmentId) {
      return appointments.find((row) => row.id === requestedAppointmentId) || null;
    }
    const now = Date.now();
    return appointments.find((row) => new Date(row.scheduled_at).getTime() >= now) || appointments[0];
  }, [appointments, requestedAppointmentId]);

  const otherAppointments = useMemo(
    () => appointments.filter((row) => row.id !== selectedAppointment?.id),
    [appointments, selectedAppointment]
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="fixed inset-0 hero-gradient z-0 pointer-events-none" />

      <header className="fixed top-0 left-0 right-0 z-50 flex items-center gap-4 px-6 py-3 glass-panel border-b border-white/20 shadow-[0_4px_24px_rgba(0,77,64,0.08)]">
        <button
          onClick={() => router.push("/patient/dashboard")}
          className="flex items-center gap-1 text-primary text-label-md font-semibold hover:bg-white/40 px-3 py-1.5 rounded-xl transition-all"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          Dashboard
        </button>
        <div className="h-5 w-px bg-outline-variant" />
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>health_and_safety</span>
          <h1 className="font-black text-primary">careIT</h1>
        </div>
        <div className="h-5 w-px bg-outline-variant" />
        <span className="text-caption text-outline font-semibold uppercase tracking-wider">Consultations</span>
      </header>

      <main className="relative z-10 max-w-4xl mx-auto px-4 pt-24 pb-xl space-y-6">
        <section className="glass-card rounded-3xl p-xl shadow-md">
          <p className="text-caption text-outline font-bold uppercase tracking-widest mb-xs">Patient Portal</p>
          <h2 className="text-headline-lg text-primary font-bold mb-sm">Consultation Access</h2>
          <p className="text-body-md text-on-surface-variant">
            When your doctor posts a meeting link for a booked appointment, it appears here on that exact appointment.
          </p>
        </section>

        {loading && (
          <div className="glass-card rounded-2xl p-xl shadow-md">
            <p className="text-body-md text-outline">Loading your appointments…</p>
          </div>
        )}

        {error && !loading && (
          <div className="glass-card rounded-2xl p-xl shadow-md border border-error/20 bg-error-container">
            <p className="text-label-md font-semibold text-error">{error}</p>
          </div>
        )}

        {!loading && !error && !selectedAppointment && (
          <div className="glass-card rounded-2xl p-xl shadow-md text-center">
            <span className="material-symbols-outlined text-outline text-5xl mb-3 block">event_busy</span>
            <p className="text-body-md text-outline">No appointments booked yet.</p>
          </div>
        )}

        {selectedAppointment && (
          <section className="glass-card rounded-3xl p-xl shadow-md space-y-md">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-caption text-outline font-bold uppercase tracking-widest mb-xs">Selected Appointment</p>
                <h3 className="text-headline-md text-primary font-bold">Appointment Ready State</h3>
                <p className="text-caption text-outline font-mono mt-xs">{selectedAppointment.id}</p>
              </div>
              <span className="rounded-full bg-primary-fixed px-3 py-1 text-caption font-bold text-primary capitalize">
                {selectedAppointment.status}
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl bg-surface-container-low px-md py-sm">
                <p className="text-caption text-outline font-bold uppercase tracking-wide mb-1">Scheduled Time</p>
                <p className="text-body-md text-on-surface font-semibold">
                  {new Date(selectedAppointment.scheduled_at).toLocaleString([], {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-low px-md py-sm">
                <p className="text-caption text-outline font-bold uppercase tracking-wide mb-1">Consultation Link</p>
                <p className="text-body-md text-on-surface font-semibold">
                  {selectedAppointment.meeting_link ? "Available" : "Waiting for doctor"}
                </p>
              </div>
            </div>

            {selectedAppointment.meeting_link ? (
              <div className="rounded-2xl border border-primary/20 bg-primary-fixed/30 p-lg">
                <div className="flex items-start gap-sm">
                  <span className="material-symbols-outlined text-primary text-[22px]" style={{ fontVariationSettings: "'FILL' 1" }}>videocam</span>
                  <div className="flex-1">
                    <p className="text-label-md text-primary font-bold">Join your consultation</p>
                    <p className="text-caption text-on-surface-variant mt-xs break-all">{selectedAppointment.meeting_link}</p>
                  </div>
                </div>
                <a
                  href={selectedAppointment.meeting_link}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-md inline-flex items-center gap-2 rounded-2xl bg-primary px-5 py-3 text-label-md font-bold text-on-primary shadow-md transition hover:scale-[1.01] active:scale-[0.99]"
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>video_call</span>
                  Join Consultation
                </a>
              </div>
            ) : (
              <div className="rounded-2xl border border-secondary/20 bg-secondary-fixed/30 p-lg">
                <p className="text-label-md text-on-secondary-container font-bold">Your doctor has not posted the meeting link yet.</p>
                <p className="text-caption text-on-secondary-container/80 mt-xs">
                  Refresh this page closer to your appointment time, or open this appointment again from the dashboard.
                </p>
              </div>
            )}
          </section>
        )}

        {otherAppointments.length > 0 && (
          <section className="space-y-sm">
            <h3 className="text-headline-md text-primary font-bold">Other Appointments</h3>
            <div className="space-y-3">
              {otherAppointments.map((appointment) => (
                <button
                  key={appointment.id}
                  onClick={() => router.push(`/patient/consultation?appointment_id=${appointment.id}`)}
                  className="w-full glass-card rounded-2xl px-md py-sm shadow-sm text-left transition hover:-translate-y-0.5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-label-md font-semibold text-on-surface">
                        {new Date(appointment.scheduled_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                      <p className="text-caption text-outline font-mono mt-1">{appointment.id}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-caption font-bold ${appointment.meeting_link ? "bg-primary-fixed text-primary" : "bg-surface-container text-outline"}`}>
                      {appointment.meeting_link ? "Link Ready" : "Waiting"}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default function PatientConsultationPage() {
  return (
    <ProtectedRoute role="patient">
      <Suspense fallback={<div className="p-8 text-outline text-body-md">Loading…</div>}>
        <ConsultationContent />
      </Suspense>
    </ProtectedRoute>
  );
}
