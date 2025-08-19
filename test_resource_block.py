#!/usr/bin/env python3
"""
Test script to check what resource blocking methods are available in DrissionPage
"""

from DrissionPage import ChromiumPage, ChromiumOptions

def test_resource_blocking():
    """Test different approaches to resource blocking in DrissionPage"""
    
    print("Testing DrissionPage resource blocking methods...")
    
    # Create browser options
    options = ChromiumOptions()
    options.headless(True)  # Use headless mode for testing
    
    try:
        # Create browser
        browser = ChromiumPage(addr_or_opts=options)
        
        print("✅ Browser created successfully")
        
        # Test different blocking methods
        methods_to_test = [
            'blocked_urls',
            'block_urls', 
            'resource_block',
            'block_resources',
            'set_blocked_urls',
            'set_block_urls'
        ]
        
        print("\n🔍 Testing available methods on browser.set:")
        set_attrs = [attr for attr in dir(browser.set) if not attr.startswith('_')]
        print(f"Available methods on browser.set: {set_attrs}")
        
        print("\n🔍 Testing browser object methods:")
        browser_attrs = [attr for attr in dir(browser) if 'block' in attr.lower() or 'resource' in attr.lower()]
        print(f"Available block/resource methods on browser: {browser_attrs}")
        
        # Try the method that seemed to work in our code
        if hasattr(browser.set, 'blocked_urls'):
            try:
                browser.set.blocked_urls(['*.jpg', '*.jpeg', '*.png'])
                print("✅ browser.set.blocked_urls() method worked!")
            except Exception as e:
                print(f"❌ browser.set.blocked_urls() failed: {e}")
        else:
            print("❌ browser.set.blocked_urls() method not found")
            
        # Try alternative methods
        for method in methods_to_test:
            if hasattr(browser.set, method):
                print(f"✅ Found method: browser.set.{method}")
                try:
                    method_func = getattr(browser.set, method)
                    if method == 'resource_block':
                        # Try the old way that failed
                        method_func(do_block=True, targets={'resource_types': ['image']})
                    else:
                        # Try URL patterns
                        method_func(['*.jpg'])
                    print(f"✅ Successfully called browser.set.{method}()")
                    break
                except Exception as e:
                    print(f"❌ browser.set.{method}() failed: {e}")
            else:
                print(f"❌ Method browser.set.{method} not found")
        
        # Close browser
        browser.quit()
        print("\n🔒 Browser closed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_resource_blocking()
