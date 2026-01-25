'use client';

import { Zap, Clock, Eye, CheckCircle, BookOpen } from 'lucide-react';
import { MetricCard } from './MetricCard';
import { useDashboardStore } from '@/stores/dashboardStore';
import { mockMetricsHistory } from '@/lib/mockApi';

export function MetricsGrid() {
    const { tasksToday, avgTaskDuration, visionCalls, successRate, learningEvents } = useDashboardStore();

    return (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
                label="Tasks Today"
                value={tasksToday}
                trend="up"
                trendValue="+12%"
                icon={<Zap size={14} />}
                sparklineData={mockMetricsHistory.tasksPerHour}
            />
            <MetricCard
                label="Avg Duration"
                value={avgTaskDuration}
                suffix="s"
                trend="down"
                trendValue="-8%"
                icon={<Clock size={14} />}
            />
            <MetricCard
                label="Vision Calls"
                value={visionCalls}
                trend="up"
                trendValue="+24%"
                icon={<Eye size={14} />}
            />
            <MetricCard
                label="Success Rate"
                value={successRate}
                suffix="%"
                trend="flat"
                trendValue="0%"
                icon={<CheckCircle size={14} />}
                sparklineData={mockMetricsHistory.successRate}
            />
            <MetricCard
                label="Learning Events"
                value={learningEvents}
                trend="up"
                trendValue="+3"
                icon={<BookOpen size={14} />}
            />
        </div>
    );
}
