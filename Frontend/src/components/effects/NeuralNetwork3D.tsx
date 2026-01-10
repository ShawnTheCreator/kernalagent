'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';

function NeuralNodes() {
    const ref = useRef<THREE.Points>(null);
    const linesRef = useRef<THREE.LineSegments>(null);

    // Generate random node positions
    const { positions, linePositions } = useMemo(() => {
        const nodeCount = 80;
        const positions = new Float32Array(nodeCount * 3);
        const lineArray: number[] = [];

        // Generate nodes in a 3D space
        for (let i = 0; i < nodeCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 5;
        }

        // Connect nearby nodes with lines
        for (let i = 0; i < nodeCount; i++) {
            for (let j = i + 1; j < nodeCount; j++) {
                const dx = positions[i * 3] - positions[j * 3];
                const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
                const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (dist < 2.5) {
                    lineArray.push(
                        positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
                        positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
                    );
                }
            }
        }

        return {
            positions,
            linePositions: new Float32Array(lineArray)
        };
    }, []);

    useFrame((state) => {
        if (ref.current) {
            ref.current.rotation.y = state.clock.elapsedTime * 0.03;
            ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.05) * 0.1;
        }
        if (linesRef.current) {
            linesRef.current.rotation.y = state.clock.elapsedTime * 0.03;
            linesRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.05) * 0.1;
        }
    });

    return (
        <group>
            {/* Neural Nodes */}
            <Points ref={ref} positions={positions} stride={3}>
                <PointMaterial
                    transparent
                    color="#ffffff"
                    size={0.08}
                    sizeAttenuation={true}
                    depthWrite={false}
                    opacity={0.8}
                />
            </Points>

            {/* Connection Lines */}
            <lineSegments ref={linesRef}>
                <bufferGeometry>
                    <bufferAttribute
                        attach="attributes-position"
                        count={linePositions.length / 3}
                        array={linePositions}
                        itemSize={3}
                    />
                </bufferGeometry>
                <lineBasicMaterial color="#3b82f6" transparent opacity={0.15} />
            </lineSegments>

            {/* Central Glow */}
            <mesh>
                <sphereGeometry args={[0.5, 32, 32]} />
                <meshBasicMaterial color="#3b82f6" transparent opacity={0.1} />
            </mesh>
        </group>
    );
}

function ParticleField() {
    const ref = useRef<THREE.Points>(null);

    const particles = useMemo(() => {
        const count = 500;
        const positions = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
        }

        return positions;
    }, []);

    useFrame((state) => {
        if (ref.current) {
            ref.current.rotation.y = state.clock.elapsedTime * 0.01;
        }
    });

    return (
        <Points ref={ref} positions={particles} stride={3}>
            <PointMaterial
                transparent
                color="#ffffff"
                size={0.02}
                sizeAttenuation={true}
                depthWrite={false}
                opacity={0.3}
            />
        </Points>
    );
}

export function NeuralNetwork3D() {
    return (
        <div className="absolute inset-0 -z-10">
            <Canvas
                camera={{ position: [0, 0, 6], fov: 60 }}
                dpr={[1, 2]}
                gl={{ antialias: true, alpha: true }}
            >
                <ambientLight intensity={0.5} />
                <NeuralNodes />
                <ParticleField />
            </Canvas>
        </div>
    );
}
