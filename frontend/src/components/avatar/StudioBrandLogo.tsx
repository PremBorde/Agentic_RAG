import React from 'react';
import { createAvatar } from '@bible-strong/avatar-react';
import '@bible-strong/avatar-react/styles.css';
import avatarJson from '../../avatar.avatar.json';
import { AvatarState } from '../../types';

export const ProceduralStudioAvatar = createAvatar(avatarJson as any);

interface StudioBrandLogoProps {
  size?: number;
  animation?: AvatarState;
}

export function StudioBrandLogo({ 
  size = 36, 
  animation = 'idle'
}: StudioBrandLogoProps) {
  const avatarPixelSize = Math.max(20, Math.round(size * 0.88));

  return (
    <div 
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '50%',
        overflow: 'hidden',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        backgroundColor: '#ffffff',
        border: size > 48 ? '2px solid #ecd8dc' : '1.5px solid #f0c2cc',
        boxShadow: size > 48 
          ? '0 8px 24px rgba(122, 28, 48, 0.08), 0 2px 6px rgba(0,0,0,0.03)' 
          : '0 1px 4px rgba(122, 28, 48, 0.08)'
      }}
    >
      <ProceduralStudioAvatar 
        size={avatarPixelSize} 
        animation={animation || 'idle'} 
      />
    </div>
  );
}
