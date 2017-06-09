// gcc -std=c++11 -shared -fPIC -lstdc++ -lrt -O3 randomfill.cpp -o randomfill.so

#include <math.h>
#include <sys/time.h>
#include <random>
#include <ctime>
#include <atomic>

#ifdef _MSC_VER
# include <intrin.h>
# define CAS(ptr, oldval, newval) \
    _InterlockedCompareExchange(ptr, newval, oldval)
#elif __GNUC__
# if __GNUC__ < 4 || (__GNUC__ == 4 && __GNUC_MINOR__ < 1)
#  error "requires GCC 4.1 or greater"
# endif
# define CAS(ptr, oldval, newval) \
    __sync_val_compare_and_swap(ptr, oldval, newval)
#else
# error "CAS not supported on this platform"
#endif

extern "C" {
  double naive(long *fillme, long size, long trials, long cardinality) {
    struct timeval startTime, endTime;

    int shift = (int)floor(log2((double)size / cardinality));

    std::mt19937 rng;
    rng.seed(std::random_device()());
    std::uniform_int_distribution<long> distribution(0, cardinality - 1);

    gettimeofday(&startTime, 0);
    for (long i = 0;  i < trials;  i++) {
      long value = distribution(rng) << shift;

      // BEGIN naively increment
      fillme[value]++;
      // END naively increment
    }
    gettimeofday(&endTime, 0);

    return (1000L * 1000L * (endTime.tv_sec - startTime.tv_sec) + (endTime.tv_usec - startTime.tv_usec)) / 1000.0 / 1000.0;
  }

  double atomic(long *fillme, long size, long trials, long cardinality) {
    struct timeval startTime, endTime;

    int shift = (int)floor(log2((double)size / cardinality));

    std::atomic<long>* fillme2 = reinterpret_cast<std::atomic<long>*>(fillme);

    std::mt19937 rng;
    rng.seed(std::random_device()());
    std::uniform_int_distribution<long> distribution(0, cardinality - 1);

    gettimeofday(&startTime, 0);
    for (long i = 0;  i < trials;  i++) {
      long value = distribution(rng) << shift;

      // BEGIN atomic increment
      fillme2[value].fetch_add(1, std::memory_order_relaxed);
      // END atomic increment
    }
    gettimeofday(&endTime, 0);

    return (1000L * 1000L * (endTime.tv_sec - startTime.tv_sec) + (endTime.tv_usec - startTime.tv_usec)) / 1000.0 / 1000.0;
  }

  double cassafe(long *fillme, long size, long trials, long cardinality, long *collisions) {
    struct timeval startTime, endTime;

    int shift = (int)floor(log2((double)size / cardinality));

    std::mt19937 rng;
    rng.seed(std::random_device()());
    std::uniform_int_distribution<long> distribution(0, cardinality - 1);

    gettimeofday(&startTime, 0);
    for (long i = 0;  i < trials;  i++) {
      long value = distribution(rng) << shift;

      // BEGIN use compare-and-swap to safely increment
      long *ptr = &fillme[value];
      long oldval = *ptr;
      long newval = oldval + 1;
      while (CAS(ptr, oldval, newval) != oldval) {
        oldval = *ptr;
        newval = oldval + 1;
        (*collisions)++;
      }
      // END use compare-and-swap to safely increment
    }
    gettimeofday(&endTime, 0);

    return (1000L * 1000L * (endTime.tv_sec - startTime.tv_sec) + (endTime.tv_usec - startTime.tv_usec)) / 1000.0 / 1000.0;
  }

  double atomic(long *fillme, long size, long trials, long cardinality, long *collisions) {
    struct timeval startTime, endTime;

    int shift = (int)floor(log2((double)size / cardinality));

    std::atomic<long>* fillme2 = reinterpret_cast<std::atomic<long>*>(fillme);

    std::mt19937 rng;
    rng.seed(std::random_device()());
    std::uniform_int_distribution<long> distribution(0, cardinality - 1);

    gettimeofday(&startTime, 0);
    for (long i = 0;  i < trials;  i++) {
      long value = distribution(rng) << shift;

      // BEGIN use atomics to safely increment
      fillme2[value].fetch_add(1, std::memory_order_relaxed);
      // END use atomics to safely increment
    }
    gettimeofday(&endTime, 0);

    return (1000L * 1000L * (endTime.tv_sec - startTime.tv_sec) + (endTime.tv_usec - startTime.tv_usec)) / 1000.0 / 1000.0;
  }
}
