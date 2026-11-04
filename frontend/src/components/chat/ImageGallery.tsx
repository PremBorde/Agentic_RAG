import React, { useState, useEffect } from 'react';
import { 
  ExternalLink, 
  Maximize2, 
  X, 
  ImageOff, 
  Globe, 
  ShieldCheck, 
  User, 
  Info,
  Layers
} from 'lucide-react';
import { ImageItem } from '../../types';
import { THEME } from '../../constants/theme';

interface ImageGalleryProps {
  images?: ImageItem[];
}

interface ImageCardProps {
  img: ImageItem;
  index: number;
  onSelect: (img: ImageItem) => void;
}

function ImageCard({ img, index, onSelect }: ImageCardProps) {
  const [src, setSrc] = useState<string>(img.thumbnail || img.image);
  const [hasTriedFallback, setHasTriedFallback] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  // If initial thumbnail fails, attempt full-res image; if that fails too, mark error
  const handleError = () => {
    if (!hasTriedFallback && img.image && src !== img.image) {
      setHasTriedFallback(true);
      setSrc(img.image);
    } else {
      setHasError(true);
      setIsLoaded(true);
    }
  };

  return (
    <div 
      style={{
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '12px',
        backgroundColor: '#ffffff',
        border: `1px solid ${THEME.beigeBorder}`,
        overflow: 'hidden',
        boxShadow: '0 2px 6px rgba(122, 28, 48, 0.04)',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
        cursor: 'pointer'
      }}
      className="image-card-hover"
      onClick={() => onSelect(img)}
      title="Click to view full preview"
    >
      {/* Thumbnail Container */}
      <div style={{
        position: 'relative',
        width: '100%',
        height: '135px',
        backgroundColor: '#f6f1eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        {/* Loading Skeleton */}
        {!isLoaded && !hasError && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f2eae2'
          }}>
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              border: `2px solid ${THEME.burgundyBorder}`,
              borderTopColor: THEME.burgundy,
              animation: 'spin 0.8s linear infinite'
            }} />
          </div>
        )}

        {/* Broken-Image Fallback */}
        {hasError ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '12px',
            color: '#8c95a0',
            textAlign: 'center'
          }}>
            <ImageOff size={24} color="#a0aec0" />
            <span style={{ fontSize: '11px', fontWeight: 500 }}>Preview restricted</span>
          </div>
        ) : (
          <img
            src={src}
            alt={img.title || `Visual reference ${index + 1}`}
            loading="lazy"
            referrerPolicy="no-referrer"
            onLoad={() => setIsLoaded(true)}
            onError={handleError}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              opacity: isLoaded ? 1 : 0,
              transition: 'opacity 0.25s ease'
            }}
          />
        )}

        {/* Hover Zoom Pill */}
        <div 
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            backgroundColor: 'rgba(26, 32, 44, 0.72)',
            backdropFilter: 'blur(4px)',
            borderRadius: '6px',
            padding: '4px',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: 0.9
          }}
          title="Inspect full image"
        >
          <Maximize2 size={12} />
        </div>

        {/* License Pill (if Creative Commons / Public Domain) */}
        {img.license && img.license !== 'Web Source' && (
          <div style={{
            position: 'absolute',
            bottom: '6px',
            left: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(4px)',
            border: '1px solid rgba(0,0,0,0.08)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '9.5px',
            fontWeight: 650,
            color: '#2d3748',
            display: 'flex',
            alignItems: 'center',
            gap: '3px'
          }}>
            <ShieldCheck size={10} color="#10b981" />
            <span>{img.license.length > 16 ? img.license.slice(0, 16) + '…' : img.license}</span>
          </div>
        )}
      </div>

      {/* Details Box */}
      <div style={{
        padding: '9px 11px',
        display: 'flex',
        flexDirection: 'column',
        gap: '5px',
        flex: 1
      }}>
        {/* Title */}
        <div style={{
          fontSize: '12px',
          fontWeight: 600,
          color: THEME.slateDark,
          lineHeight: '1.35',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>
          {img.title || "Visual Reference"}
        </div>

        {/* Source Link & Domain */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 'auto',
          paddingTop: '4px',
          fontSize: '11px',
          color: '#718096'
        }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            maxWidth: '120px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            <Globe size={11} color="#a0aec0" />
            {img.source || "Web"}
          </span>

          <a
            href={img.url || img.image}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Open original webpage in new tab"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
              color: THEME.burgundy,
              fontWeight: 600,
              textDecoration: 'none',
              padding: '2px 4px',
              borderRadius: '4px',
              transition: 'background-color 0.15s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fdf0f3'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <span>Visit</span>
            <ExternalLink size={10} />
          </a>
        </div>
      </div>
    </div>
  );
}

export function ImageGallery({ images }: ImageGalleryProps) {
  const [selectedImg, setSelectedImg] = useState<ImageItem | null>(null);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedImg(null);
      }
    };
    if (selectedImg) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedImg]);

  if (!images || images.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: '12px', width: '100%' }}>
      {/* Gallery Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '10px',
        paddingBottom: '6px',
        borderBottom: `1px solid ${THEME.beigeBorder}`
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          fontWeight: 650,
          color: THEME.slateDark
        }}>
          <Layers size={14} color={THEME.burgundy} />
          <span>Visual References & Diagrams</span>
          <span style={{
            fontSize: '11px',
            fontWeight: 500,
            padding: '1px 6px',
            borderRadius: '10px',
            backgroundColor: '#f4ede6',
            color: '#6b7280'
          }}>
            {images.length}
          </span>
        </div>
        <span style={{ fontSize: '11px', color: '#9ca3af' }}>Click to expand</span>
      </div>

      {/* Responsive Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(185px, 1fr))',
        gap: '10px',
        width: '100%'
      }}>
        {images.map((img, idx) => (
          <ImageCard
            key={`${img.url || img.image}-${idx}`}
            img={img}
            index={idx}
            onSelect={(selected) => setSelectedImg(selected)}
          />
        ))}
      </div>

      {/* Copyright & Licensing Attribution Disclaimer */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        marginTop: '8px',
        fontSize: '10.5px',
        color: '#94a3b8'
      }}>
        <Info size={11} color="#94a3b8" />
        <span>
          Images subject to copyright by their respective publishers. Open original links for licensing details.
        </span>
      </div>

      {/* Fullscreen Lightbox Modal */}
      {selectedImg && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.78)',
            backdropFilter: 'blur(8px)',
            zIndex: 99999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            animation: 'fadeIn 0.2s ease-out'
          }}
          onClick={() => setSelectedImg(null)}
        >
          <div 
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '16px',
              maxWidth: '820px',
              width: '100%',
              maxHeight: '92vh',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 45px rgba(0,0,0,0.3)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 18px',
              borderBottom: `1px solid ${THEME.beigeBorder}`,
              backgroundColor: '#fdfbf9'
            }}>
              <div style={{
                fontSize: '13px',
                fontWeight: 650,
                color: THEME.slateDark,
                maxWidth: '680px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {selectedImg.title || "Visual Reference"}
              </div>

              <button
                type="button"
                onClick={() => setSelectedImg(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '5px',
                  borderRadius: '6px',
                  color: '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.15s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                title="Close (ESC)"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Image Display Area */}
            <div style={{
              backgroundColor: '#111827',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '260px',
              maxHeight: '62vh',
              overflow: 'hidden'
            }}>
              <img
                src={selectedImg.image || selectedImg.thumbnail}
                alt={selectedImg.title}
                referrerPolicy="no-referrer"
                style={{
                  maxWidth: '100%',
                  maxHeight: '60vh',
                  objectFit: 'contain'
                }}
              />
            </div>

            {/* Modal Footer & Actions */}
            <div style={{
              padding: '14px 18px',
              backgroundColor: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Globe size={12} color="#64748b" />
                    {selectedImg.source || "Web"}
                  </span>
                  {selectedImg.license && (
                    <span style={{
                      fontSize: '11px',
                      padding: '2px 7px',
                      borderRadius: '4px',
                      backgroundColor: '#eff6ff',
                      color: '#1d4ed8',
                      fontWeight: 500,
                      border: '1px solid #bfdbfe'
                    }}>
                      {selectedImg.license}
                    </span>
                  )}
                </div>
                {selectedImg.author && (
                  <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <User size={11} />
                    <span>Author / Attribution: {selectedImg.author}</span>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <a
                  href={selectedImg.image}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '7px 12px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 600,
                    backgroundColor: '#f1f5f9',
                    color: '#334155',
                    textDecoration: 'none',
                    border: '1px solid #e2e8f0',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e2e8f0'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
                >
                  <span>Direct Image</span>
                  <ExternalLink size={12} />
                </a>

                <a
                  href={selectedImg.url || selectedImg.image}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '7px 14px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 650,
                    backgroundColor: THEME.burgundy,
                    color: '#ffffff',
                    textDecoration: 'none',
                    boxShadow: '0 2px 6px rgba(122, 28, 48, 0.2)',
                    transition: 'background-color 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = THEME.burgundyHover}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = THEME.burgundy}
                >
                  <span>Visit Website</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

